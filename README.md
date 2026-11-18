# Lab05 — Desempenho e acessibilidade do site do Mercado Livre

Trabalho do Lab05 ("Experimento em Software Real") da disciplina Laboratório de Experimentação de Software, Engenharia de Software, PUC Minas.

## Sobre o estudo

O grupo mede, de fora e como um usuário comum, o **desempenho** e a **acessibilidade** do site do Mercado Livre (mercadolivre.com.br). As medições vêm da API do **PageSpeed Insights** (PSI), chamada por um workflow agendado no **GitHub Actions**. O estudo compara tipos de página, perfis de dispositivo (móvel e desktop) e horários, e verifica se a medição sintética reflete os usuários reais.

O objeto de estudo é o site em operação. GitHub e GitHub Actions são só instrumentos de coleta. A coleta respeita no máximo 1 requisição por segundo, o `robots.txt` e os termos de uso, e não usa login nem coleta dados pessoais.

## Kanban

O acompanhamento das tarefas fica no GitHub Projects: **https://github.com/users/ArlindoSPJr/projects/7**

