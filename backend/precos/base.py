from dataclasses import asdict, dataclass, field


@dataclass
class Oferta:
    titulo: str
    preco: float
    moeda: str
    link: str | None = None
    vendedor: str | None = None
    condicao: str | None = None


@dataclass
class ResultadoFonte:
    fonte: str
    situacao: str
    mensagem: str | None = None
    termo: str | None = None
    ofertas: list[Oferta] = field(default_factory=list)

    def para_dict(self):
        dados = asdict(self)
        precos = sorted(o.preco for o in self.ofertas if o.moeda == "BRL")

        dados["resumo"] = (
            {
                "menor": precos[0],
                "mediana": precos[len(precos) // 2]
                if len(precos) % 2
                else round((precos[len(precos) // 2 - 1] + precos[len(precos) // 2]) / 2, 2),
                "maior": precos[-1],
                "quantidade": len(precos),
            }
            if precos
            else None
        )

        return dados


class FontePreco:
    """Interface das fontes externas de preço."""

    nome = "Fonte"

    def configurada(self) -> bool:
        raise NotImplementedError

    def buscar(self, termo: str, limite: int = 10) -> ResultadoFonte:
        raise NotImplementedError
