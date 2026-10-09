"""Consulta de preços de referência.

Cada fonte externa implementa `FontePreco`. Para adicionar uma nova API de
preços, crie uma classe com `nome`, `configurada()` e `buscar(termo)` e inclua
uma instância em `FONTES` (backend/precos/servico.py).
"""
