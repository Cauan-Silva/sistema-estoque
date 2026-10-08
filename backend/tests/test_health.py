def test_health(client):
    resposta = client.get(
        "/health"
    )

    assert resposta.status_code == 200

    assert resposta.json() == {
        "status": "online"
    }

def test_frontend_disponivel(client):
    resposta = client.get("/app/")

    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert "Estoque" in resposta.text
    assert resposta.headers["cache-control"] == "no-cache"


def test_arquivos_do_frontend_sem_cache(client):
    resposta = client.get("/app/js/app.js")

    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-cache"
