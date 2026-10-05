"""Download com cache em disco, limite de taxa por host e retentativas."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

USER_AGENT = "QuemMandaAqui/0.1 (+https://quemmandaaqui.com.br)"
ESPERAS_RETENTATIVA = (1, 2, 4)  # segundos; 1 tentativa + 3 retentativas
_INVALIDOS = re.compile(r'[<>:"|?*\\\x00-\x1f]')

# Próximo instante liberado por host; compartilhado por todo o processo.
_limitadores: dict[str, float] = {}


class ErroDownload(Exception):
    """Falha ao baixar `url`. `status` é None em falhas de rede."""

    def __init__(self, url: str, status: int | None):
        self.url = url
        self.status = status
        super().__init__(f"falha ao baixar {url} (status {status})")


def _novo_cliente(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=15.0),
        transport=transport,
    )


def _caminho_cache(url: str, cache_dir: Path) -> Path:
    partes = urlsplit(url)
    host = _INVALIDOS.sub("_", partes.netloc or "sem-host")
    segmentos = [_INVALIDOS.sub("_", s) for s in partes.path.split("/") if s not in ("", ".", "..")]
    nome = segmentos.pop() if segmentos else "index"
    if partes.query:
        h = hashlib.sha1(partes.query.encode("utf-8")).hexdigest()[:10]
        base, ext = os.path.splitext(nome)
        nome = f"{base}__{h}{ext}"
    # Sufixo fixo: o arquivo é sempre folha e nunca colide com um diretório
    # de outra URL (ex.: /a e /a/b).
    return cache_dir.joinpath(host, *segmentos, (nome.rstrip(". ") or "index") + ".dados")


def _aguardar_vez(host: str, max_por_segundo: float, relogio, dormir) -> None:
    intervalo = 1.0 / max_por_segundo
    agora = relogio()
    liberado = _limitadores.get(host, agora)
    if liberado > agora:
        dormir(liberado - agora)
        agora = liberado
    _limitadores[host] = max(agora, liberado) + intervalo


def _tentar(cliente, url, destino: Path, host, max_por_segundo, relogio, dormir) -> None:
    """Uma tentativa. Levanta ErroDownload; `_Retentavel` indica que vale repetir."""
    _aguardar_vez(host, max_por_segundo, relogio, dormir)
    parcial = destino.with_name(destino.name + ".parcial")
    try:
        with cliente.stream("GET", url) as resp:
            if resp.status_code != 200:
                raise _Retentavel(url, resp.status_code) if resp.status_code >= 500 else ErroDownload(url, resp.status_code)
            with open(parcial, "wb") as f:
                for pedaco in resp.iter_bytes(1 << 20):
                    f.write(pedaco)
        os.replace(parcial, destino)
    except httpx.HTTPError as e:
        raise _Retentavel(url, None) from e
    finally:
        parcial.unlink(missing_ok=True)


class _Retentavel(ErroDownload):
    pass


def baixar(
    url: str,
    *,
    cache_dir: Path = Path(".cache"),
    max_por_segundo: float = 4.0,
    forcar: bool = False,
    _cliente: httpx.Client | None = None,
    _relogio: Callable[[], float] = time.monotonic,
    _dormir: Callable[[float], None] = time.sleep,
) -> Path:
    """Baixa `url` para o cache (se ainda não estiver lá) e devolve o caminho local."""
    destino = _caminho_cache(url, Path(cache_dir))
    if destino.exists() and not forcar:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    host = urlsplit(url).netloc
    cliente = _cliente or _novo_cliente()
    try:
        for espera in (*ESPERAS_RETENTATIVA, None):
            try:
                _tentar(cliente, url, destino, host, max_por_segundo, _relogio, _dormir)
                return destino
            except _Retentavel as e:
                if espera is None:
                    raise ErroDownload(url, e.status) from e.__cause__
                _dormir(espera)
    finally:
        if _cliente is None:
            cliente.close()
    raise AssertionError("inalcançável")  # pragma: no cover


def baixar_json(url: str, **kw: Any) -> Any:
    """Baixa (com cache) e decodifica JSON em UTF-8, aceitando BOM."""
    return json.loads(baixar(url, **kw).read_text(encoding="utf-8-sig"))
