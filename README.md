# Lab05 — Desempenho e acessibilidade do site do Mercado Livre

Trabalho do Lab05 ("Experimento em Software Real") da disciplina Laboratório de Experimentação de Software, Engenharia de Software, PUC Minas.

## Sobre o estudo

O grupo mede, de fora e como um usuário comum, o **desempenho** e a **acessibilidade** do site do Mercado Livre (mercadolivre.com.br). As medições vêm da API do **PageSpeed Insights** (PSI), chamada por um workflow agendado no **GitHub Actions**. O estudo compara tipos de página, perfis de dispositivo (móvel e desktop) e horários, e verifica se a medição sintética reflete os usuários reais.

O objeto de estudo é o site em operação. GitHub e GitHub Actions são só instrumentos de coleta. A coleta respeita no máximo 1 requisição por segundo, o `robots.txt` e os termos de uso, e não usa login nem coleta dados pessoais.

## Kanban

O acompanhamento das tarefas fica no GitHub Projects: **https://github.com/users/ArlindoSPJr/projects/7**

## Documentos de referência

- [Design do estudo](docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md): fonte da verdade sobre o método, as hipóteses, a coleta e a análise.
- [Issues por onda e sprint](docs/superpowers/plans/2026-11-16-issues-ondas.md): divisão do trabalho, espelhada nas issues do GitHub e no Kanban.
- [Enunciado do Lab05](Lab05Medicao.pdf).

## Papéis

Os papéis são fixos e seguem o §7 do design. A definição de quem ocupa cada papel ainda está em aberto (§9 do design).

| Papel | Responsabilidade | Integrante |
|---|---|---|
| A | Planejamento e Método | a definir |
| B | Instrumentação e Operação | a definir |
| C | Análise e Impacto | a definir |

## Cronograma

| Período | Etapa |
|---|---|
| 16/11 – 26/11 | Sprint conjunta S01 + S02: proposta, coleta e análise |
| 26/11 | **Entrega conjunta S01 + S02** |
| 27/11 – 03/12 | Sprint S03: impacto, conclusões e entrega final |
| 03/12 | Ensaio da apresentação |
| 04/12 | **Apresentação do grupo** (10 min) |

O detalhamento por onda e as datas críticas da coleta estão no §7 do design.

## Regra de commit

- Toda mensagem de commit referencia a issue do GitHub pelo número, com `Refs #N`.
- `Closes #N` só no PR que conclui a issue; commits usam `Refs #N`.

## Como reproduzir

Em construção. Esta seção será escrita na issue #30 (B-11).
