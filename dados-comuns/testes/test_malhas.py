from qma_comum.malhas import baixar_malhas


def test_malhas_nome_arquivos(tmp_path):
    pedidos = []

    def falso(url, **kw):
        pedidos.append(url)
        arq = tmp_path / f"cache{len(pedidos)}"
        arq.write_text('{"type":"Topology"}', encoding="utf-8")
        return arq

    saida = tmp_path / "malhas"
    baixar_malhas(["GO", "DF"], saida, _baixar=falso)

    assert sorted(p.name for p in saida.iterdir()) == ["br-uf.json", "df.json", "go.json"]
    assert "paises/BR" in pedidos[0] and "intrarregiao=UF" in pedidos[0]
    assert "estados/GO" in pedidos[1] and "intrarregiao=municipio" in pedidos[1]
    assert all("qualidade=minima" in u for u in pedidos)
