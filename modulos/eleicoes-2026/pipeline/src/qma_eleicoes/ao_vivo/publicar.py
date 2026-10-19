"""Publicação dos JSONs do ao vivo: bucket R2 (S3) ou pasta local (ensaio e testes)."""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
import tempfile
from pathlib import Path

log = logging.getLogger("qma_eleicoes.ao_vivo")

CONTENT_TYPE = "application/json; charset=utf-8"
CACHE_CONTROL = "public, max-age=20"
PREFIXO_PADRAO = "ao-vivo/"
CONTROLE_PADRAO = {"projecao_ligada": False}
_PREFIXO_MONTAR = "ao-vivo/"  # `montar` devolve caminhos que começam assim


def _normalizar_prefixo(prefixo: str) -> str:
    return prefixo if not prefixo or prefixo.endswith("/") else prefixo + "/"


def _corpo(conteudo) -> bytes:
    return json.dumps(conteudo, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _controle(texto: bytes | str | None) -> dict:
    """Ausente ou inválido → projeção desligada (lado seguro)."""
    if texto is None:
        return dict(CONTROLE_PADRAO)
    try:
        dados = json.loads(texto)
    except ValueError:
        log.warning("controle.json inválido; projeção desligada")
        return dict(CONTROLE_PADRAO)
    return dados if isinstance(dados, dict) else dict(CONTROLE_PADRAO)


def _bundle_do_sistema() -> str | None:
    """Certificados raiz do Windows num arquivo PEM (None fora do Windows).

    `truststore.inject_into_ssl()` entra em recursão infinita com o botocore no
    Python 3.12 (o setter de `SSLContext.options` do stdlib enxerga a classe
    trocada), então a cadeia do SO é passada ao boto3 como `verify=<arquivo>`.
    """
    if sys.platform != "win32":
        return None
    import certifi

    pems = [Path(certifi.where()).read_text(encoding="ascii")]
    for loja in ("ROOT", "CA"):
        for der, codificacao, _ in ssl.enum_certificates(loja):
            if codificacao == "x509_asn":
                pems.append(ssl.DER_cert_to_PEM_cert(der))
    arquivo = Path(tempfile.gettempdir()) / "qma-ca-bundle.pem"
    arquivo.write_text(os.linesep.join(pems), encoding="ascii")
    return str(arquivo)


class _Publicador:
    def __init__(self, prefixo: str = PREFIXO_PADRAO):
        self.prefixo = _normalizar_prefixo(prefixo)

    def _chave(self, caminho: str) -> str:
        return self.prefixo + caminho.removeprefix(_PREFIXO_MONTAR)

    def _ordenados(self, arquivos: dict[str, object]) -> list[tuple[str, bytes]]:
        """Chave final e corpo; `estado.json` sempre por último."""
        chave_estado = self._chave(_PREFIXO_MONTAR + "estado.json")
        itens = [(self._chave(c), _corpo(v)) for c, v in sorted(arquivos.items())]
        return sorted(itens, key=lambda kv: kv[0] == chave_estado)  # sort estável


class PublicadorR2(_Publicador):
    def __init__(self, bucket: str, *, prefixo: str = PREFIXO_PADRAO, _cliente=None):
        super().__init__(prefixo)
        self.bucket = bucket
        self._cliente = _cliente

    @classmethod
    def do_ambiente(cls, prefixo: str = PREFIXO_PADRAO) -> PublicadorR2:
        """Lê R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY e R2_BUCKET."""
        import boto3

        cliente = boto3.client(
            "s3",
            endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            region_name="auto",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            verify=_bundle_do_sistema() or True,  # certificados do SO (TLS interceptado no Windows)
        )
        return cls(os.environ["R2_BUCKET"], prefixo=prefixo, _cliente=cliente)

    def publicar(self, arquivos: dict[str, object]) -> None:
        for chave, corpo in self._ordenados(arquivos):
            self._cliente.put_object(
                Bucket=self.bucket,
                Key=chave,
                Body=corpo,
                ContentType=CONTENT_TYPE,
                CacheControl=CACHE_CONTROL,
            )

    def ler_controle(self) -> dict:
        from botocore.exceptions import ClientError

        try:
            resposta = self._cliente.get_object(Bucket=self.bucket, Key="controle.json")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return dict(CONTROLE_PADRAO)
            raise
        return _controle(resposta["Body"].read())


class PublicadorLocal(_Publicador):
    def __init__(self, pasta: str | Path, *, prefixo: str = PREFIXO_PADRAO):
        super().__init__(prefixo)
        self.pasta = Path(pasta)

    def publicar(self, arquivos: dict[str, object]) -> None:
        for chave, corpo in self._ordenados(arquivos):
            destino = self.pasta / chave
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(corpo)

    def ler_controle(self) -> dict:
        arquivo = self.pasta / "controle.json"
        return _controle(arquivo.read_bytes() if arquivo.exists() else None)
