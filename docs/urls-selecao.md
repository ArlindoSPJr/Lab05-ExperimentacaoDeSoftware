# Seleção das URLs do estudo (issue #5)

Este documento registra como as 19 URLs (+ reservas) de `config/urls.csv` foram escolhidas, para que a seleção possa ser refeita e auditada. Os critérios vêm do §5.6 do design (`docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`).

- **Data da seleção:** 17/11/2026 (navegador Chrome, **sem login**, a partir de Belo Horizonte/MG).
- **Ritmo de acesso:** navegação manual/assistida e verificações por `fetch`/`curl` com intervalo de 1,5 s a 2 s entre requisições (≤ 1 req/s), sem login e sem coleta de dados pessoais.
- **Contrato do arquivo:** colunas `slot_id,tipo,url,url_reserva,host,mlb_id,criterio,data_selecao`, consumidas por `load_urls` do coletor (issue #8). `url_reserva` e `mlb_id` ficam vazios onde não se aplicam.

## Resumo

| Tipo | Slots | Situação |
|---|---|---|
| Categoria | `cat-1` … `cat-6` | Completo |
| Busca | `bus-1` … `bus-6` | Completo (URLs montadas pelo padrão; ver observações) |
| Produto | `pro-1` … `pro-6` | **PENDENTE (preenchimento manual)**: lista "Mais vendidos" bloqueada por CAPTCHA para o agente |
| Home | `home` | Completo |

## 1. Categorias (`cat-1` … `cat-6`)

**Critério:** as 6 categorias de maior destaque no menu principal, operacionalizado como **as 6 primeiras entradas do menu "Categorias" (ordem de cima para baixo) que levam a uma página de categoria padrão `/c/<slug>` que não redireciona**. Assim, as 6 URLs usam o mesmo modelo de página.

Captura do menu: `docs/img/menu-2026-11-17.png` (sem login; a localização de entrega exibida no cabeçalho foi ocultada antes da captura).

Passo a passo (17/11/2026):

1. Abrir `https://www.mercadolivre.com.br/` sem login e passar o mouse sobre **Categorias**.
2. Ler as entradas do menu na ordem e os links de cada uma (extraídos do DOM da página):

| Pos. | Entrada do menu | Link | Decisão |
|---|---|---|---|
| 1 | Veículos | `/veiculos/` | Excluída: vertical de classificados, não é página `/c/` |
| 2 | Supermercado | `/ofertas/supermercado` | Excluída: página de ofertas, não é `/c/` |
| 3 | Tecnologia | (sem link próprio; abre painel) | Usada a **1ª subcategoria do painel**: Celulares e Telefones → `cat-1` |
| 4 | Casa e Móveis | `/c/casa-moveis-e-decoracao` | `cat-2` |
| 5 | Eletrodomésticos | `/c/eletrodomesticos` | `cat-3` |
| 6 | Esportes e Fitness | `/c/esportes-e-fitness` | `cat-4` |
| 7 | Ferramentas | `/c/ferramentas` | Excluída: **redireciona para a home** (finalUrl `https://www.mercadolivre.com.br/`) |
| 8 | Construção | `/c/construcao` | Excluída: **redireciona para a home** |
| 9 | Indústria e Comércio | `/c/industria-e-comercio` | `cat-5` |
| 10 | Para seu Negócio | `/e/negocios` | Excluída: página `/e/`, não `/c/` |
| 11 | Pet Shop | `/c/animais` | `cat-6` |

3. Conferir o `finalUrl` de cada URL escolhida (seguindo redirecionamentos): todas retornaram HTTP 200 sem redirecionamento, em `www.mercadolivre.com.br`. A home e `/c/celulares-e-telefones` e `/c/animais` também foram conferidas por `curl` (cliente sem cookies), com o mesmo resultado.

## 2. Busca (`bus-1` … `bus-6`)

**Critério:** 1 termo genérico por categoria escolhida, sem filtros, no padrão `https://lista.mercadolivre.com.br/<termo>` (minúsculas, sem acentos, preferindo uma palavra). `url_reserva` = um segundo termo genérico da mesma categoria. Os termos foram escolhidos pelo grupo como o nome genérico de um tipo de produto típico da categoria (é uma escolha de julgamento, registrada aqui para transparência).

| Slot | Categoria | Termo | Reserva |
|---|---|---|---|
| `bus-1` | Celulares e Telefones | `celular` | `smartphone` |
| `bus-2` | Casa e Móveis | `sofa` | `mesa` |
| `bus-3` | Eletrodomésticos | `geladeira` | `fogao` |
| `bus-4` | Esportes e Fitness | `bicicleta` | `esteira` |
| `bus-5` | Indústria e Comércio | `embalagem` | `balanca` |
| `bus-6` | Pet Shop | `racao` | `coleira` |

`host` = `lista.mercadolivre.com.br`, pelo padrão da URL. **As páginas de busca não foram abertas pelo agente** (decisão do coordenador; ver observações abaixo).

**Evidência de que a busca abre sem login no PSI:** em 18/11/2026, às 16h15 BRT, o coordenador rodou o PageSpeed Insights (pagespeed.web.dev, perfil celular, Lighthouse 13.6.0) para `https://lista.mercadolivre.com.br/celular`. O Lighthouse renderizou a página de resultados real (lista de celulares com preços, com um banner "Abra o app"), e não um CAPTCHA. Também havia dados de campo (CrUX) para a URL.

## 3. Produto (`pro-1` … `pro-6`) — PENDENTE (preenchimento manual)

**Critério:** o 1º item da lista "Mais vendidos" de cada uma das 6 categorias (`url`), com o 2º item da mesma lista como `url_reserva`.

**Por que está pendente:** em 17/11/2026, as listas ranqueadas `https://www.mercadolivre.com.br/mais-vendidos/MLB<id>` levaram o navegador do agente a uma tela de CAPTCHA (`/captcha/wall`) duas vezes. O CAPTCHA não foi contornado. A página-índice `https://www.mercadolivre.com.br/mais-vendidos` abriu, mas seus carrosséis misturam itens "BLACK FRIDAY"/"OFERTA IMPERDÍVEL" e não são o ranking, e não incluem todas as 6 categorias. Por isso não foram usados.

IDs de categoria vistos na página-índice em 17/11/2026: Celulares e Telefones = `MLB1051`, Eletrodomésticos = `MLB5726`, Esportes e Fitness = `MLB1276`. IDs de Casa e Móveis, Indústria e Comércio e Pet Shop: **não encontrados** (não aparecem na página-índice; procurar como no passo 2 abaixo).

**Passo a passo para o integrante A (navegador comum, sem login):**

1. Abrir `https://www.mercadolivre.com.br/mais-vendidos` em janela anônima (sem login).
2. Para cada categoria (`pro-1` Celulares e Telefones, `pro-2` Casa e Móveis, `pro-3` Eletrodomésticos, `pro-4` Esportes e Fitness, `pro-5` Indústria e Comércio, `pro-6` Pet Shop), abrir a lista ranqueada da categoria: pelo link "Ver mais" da seção correspondente, ou pelo link "Mais vendidos" na página da categoria (`/c/<slug>`), ou pelo filtro de categoria da própria página. A lista correta mostra os itens numerados (1º, 2º, …) e tem URL `.../mais-vendidos/MLB<id>`. Se aparecer CAPTCHA, resolvê-lo manualmente.
3. Clicar no **1º item** e copiar a URL **sem os parâmetros** após `?` e `#` → coluna `url`.
4. Voltar, clicar no **2º item** e copiar a URL da mesma forma → coluna `url_reserva`.
5. `mlb_id`: o ID MLB do 1º item como aparece na URL (ex.: `/p/MLB12345678` → `MLB12345678`; `produto.mercadolivre.com.br/MLB-1234567890-...` → `MLB1234567890`, sem hífen). Registrar se o ID é de catálogo (`/p/`) ou de anúncio.
6. `host`: o host da barra de endereço **depois** que a página do 1º item terminar de carregar (finalUrl), ex.: `www.mercadolivre.com.br` ou `produto.mercadolivre.com.br`.
7. Conferir em janela anônima que as duas URLs abrem sem login.
8. Substituir os `PENDENTE` da linha em `config/urls.csv`. Manter `data_selecao` como a data real do preenchimento e anotar aqui (seção 6) a data, a hora e o ID da categoria (`MLB<id>`) de cada lista usada.
9. Commit com `Refs #5` (ou `Closes #5` se fechar a issue). Fazer isso **antes do início da coleta** (18/11, 20h07).

## 4. Home (`home`)

`https://www.mercadolivre.com.br/`, tipo `home`, sem reserva. finalUrl = `https://www.mercadolivre.com.br/` (HTTP 200, sem redirecionamento). É referência descritiva e não entra nos testes de tipo de página (§5.6).

## 5. Observações, riscos e notas de validade

- **Bloqueio de cliente automatizado (risco/observação).** Em 17/11/2026, sem login:
  - `curl` para `https://lista.mercadolivre.com.br/<termo>` (os 6 termos) foi redirecionado para `https://www.mercadolivre.com.br/gz/account-verification?go=...`;
  - no Chrome controlado pelo agente, `lista.mercadolivre.com.br/celular` e `/mais-vendidos/MLB1051` caíram em `/captcha/wall`;
  - a home e as páginas `/c/` abriram normalmente nos dois clientes.

  O teste do PSI de 18/11 (seção 2) mostra que o Lighthouse do PSI recebeu a página real. Ainda assim, o coletor (issue #8) deve detectar bloqueio em cada medição (ex.: `finalUrl` contendo `captcha` ou `account-verification`, ou título "Segurança — Mercado Livre") e descartar ou marcar essas linhas. Uma medição de CAPTCHA no lugar da página mediria outra coisa.
- **Banner "Abra o app" (validade de construto).** No perfil móvel, a busca exibe um banner de convite para o app. Ele faz parte do que o usuário móvel recebe, mas pode afetar o LCP e as auditorias de acessibilidade. Registrar isso na seção de ameaças à validade (construto).
- **Redirecionamentos de categorias.** `Ferramentas` e `Construção` estão no menu, mas seus links `/c/` levam à home. Isso foi tratado como critério de exclusão, porque medir essas URLs seria medir a home.
- **Período promocional.** Em 17/11/2026 o site já exibia selos "BLACK FRIDAY". A seleção de produtos depende do ranking do dia, e o ranking muda com as promoções.
- **robots.txt:** a checagem destas URLs contra o `robots.txt` é feita na issue #6 (ética).

## 6. Registro do preenchimento manual dos produtos

| Slot | Data/hora | Lista usada (`MLB<id>`) | Observações |
|---|---|---|---|
| `pro-1` | PENDENTE | `MLB1051` (a confirmar) | |
| `pro-2` | PENDENTE | não encontrado | |
| `pro-3` | PENDENTE | `MLB5726` (a confirmar) | |
| `pro-4` | PENDENTE | `MLB1276` (a confirmar) | |
| `pro-5` | PENDENTE | não encontrado | |
| `pro-6` | PENDENTE | não encontrado | |
