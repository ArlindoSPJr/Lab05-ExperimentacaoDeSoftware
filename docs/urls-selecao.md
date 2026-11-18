# Seleção das URLs do estudo (issue #5)

Este documento registra como as 19 URLs (+ reservas de produto) de `config/urls.csv` foram escolhidas, para que a seleção possa ser refeita e auditada. Os critérios vêm do §5.6 do design (`docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`).

- **Data da seleção:** 17/11/2026, com revisão das categorias em 18/11/2026 (navegador Chrome, **sem login**, a partir de Belo Horizonte/MG).
- **Ritmo de acesso:** páginas abertas uma a uma, com ≥ 3 s entre carregamentos no navegador e 1,5 s a 2 s entre requisições `fetch`/`curl` (≤ 1 req/s), sem login e sem coleta de dados pessoais.
- **Contrato do arquivo:** colunas `slot_id,tipo,url,url_reserva,host,mlb_id,criterio,data_selecao`, consumidas por `load_urls` do coletor (issue #8). `url_reserva` só é preenchida para produtos (design §8, "Política de substituição": URLs de categoria e busca não são trocadas). `mlb_id` só se aplica a produtos.

## Resumo

| Tipo | Slots | Situação |
|---|---|---|
| Categoria | `cat-1` … `cat-6` | Completo |
| Busca | `bus-1` … `bus-6` | Completo (URLs montadas pelo padrão; ver observações) |
| Produto | `pro-1` … `pro-6` | **PENDENTE (preenchimento manual)**: lista "Mais vendidos" bloqueada por CAPTCHA para o agente |
| Home | `home` | Completo |

## 1. Categorias (`cat-1` … `cat-6`)

**Critério (regra operacional):** as 6 categorias de maior destaque no menu principal são **as 6 primeiras entradas do menu "Categorias", na ordem de cima para baixo, que levam a uma página de categoria padrão `/c/<slug>`**. Ficam fora as entradas que levam a páginas de outro modelo (classificados, ofertas, `/e/`). **Exceção explícita:** uma entrada sem página própria que apenas abre um painel de subcategorias conta pela **1ª subcategoria do painel** (a primeira do canto superior esquerdo), desde que esta seja uma página `/c/`. É o caso de Tecnologia → Celulares e Telefones. Essa exceção mistura níveis da hierarquia; ver a seção 5.

Captura do menu: `docs/img/menu-2026-11-17.png` (sem login; a localização de entrega exibida no cabeçalho foi ocultada antes da captura).

Passo a passo:

1. Abrir `https://www.mercadolivre.com.br/` sem login e passar o mouse sobre **Categorias** (17/11/2026).
2. Ler as entradas do menu na ordem e os links de cada uma (extraídos do DOM da página):

| Pos. | Entrada do menu | Link | Decisão |
|---|---|---|---|
| 1 | Veículos | `/veiculos/` | Excluída: vertical de classificados, não é página `/c/` |
| 2 | Supermercado | `/ofertas/supermercado` | Excluída: página de ofertas, não é `/c/` |
| 3 | Tecnologia | (sem link próprio; abre painel) | Pela exceção: 1ª subcategoria do painel, Celulares e Telefones (`/c/celulares-e-telefones`) → `cat-1` |
| 4 | Casa e Móveis | `/c/casa-moveis-e-decoracao` | `cat-2` |
| 5 | Eletrodomésticos | `/c/eletrodomesticos` | `cat-3` |
| 6 | Esportes e Fitness | `/c/esportes-e-fitness` | `cat-4` |
| 7 | Ferramentas | `/c/ferramentas` | `cat-5` |
| 8 | Construção | `/c/construcao` | `cat-6` |
| 9+ | Indústria e Comércio, Para seu Negócio, Pet Shop, … | — | Não usadas (as 6 vagas já foram preenchidas) |

3. Conferir no navegador que cada URL abre como categoria real (ver método e resultados abaixo).

**Método da conferência (18/11/2026):** Chrome sem login (cabeçalho com "Crie a sua conta / Entre"). Cada URL foi aberta na barra de endereço; depois de ~3 s de carregamento, foram lidos por JavaScript na página `location.href` (host + caminho) e `document.title`, e também o texto do `<h1>`.

| Slot | URL pedida | `location.href` após carregar | `document.title` / `<h1>` |
|---|---|---|---|
| `cat-1` | `/c/celulares-e-telefones` | `www.mercadolivre.com.br/c/celulares-e-telefones` | Celulares e telefones |
| `cat-2` | `/c/casa-moveis-e-decoracao` | `www.mercadolivre.com.br/c/casa-moveis-e-decoracao` | Casa, móveis e decoração |
| `cat-3` | `/c/eletrodomesticos` | `www.mercadolivre.com.br/c/eletrodomesticos` | Eletrodomésticos |
| `cat-4` | `/c/esportes-e-fitness` | `www.mercadolivre.com.br/c/esportes-e-fitness` | **Projeto Verão** (campanha sazonal; ver seção 5) |
| `cat-5` | `/c/ferramentas` | `www.mercadolivre.com.br/c/ferramentas` | Ferramentas |
| `cat-6` | `/c/construcao` | `www.mercadolivre.com.br/c/construcao` | Construção |
| `home` | `/` | `www.mercadolivre.com.br/` | Mercado Livre Brasil - Frete Grátis no mesmo dia |

**Correção em relação à 1ª versão (17/11/2026).** A primeira versão excluiu Ferramentas e Construção porque em 17/11 elas pareceram redirecionar para a home. Essa observação veio de um `fetch` sem cookies (`credentials: 'omit'`) feito a partir da página do ML e de uma navegação no Chrome para `/c/ferramentas`, que terminou em `location.pathname = "/"`. Não foi feita captura nem registro do `finalUrl` no PSI. Em 18/11 a revisão independente e a nova conferência acima mostraram as duas abrindo como categoria real. Como o redirecionamento não se reproduziu e não há prova dele, as duas voltaram pela regra (posições 7 e 8), e Indústria e Comércio e Pet Shop saíram.

**O que o `curl` mostra e o que não mostra.** `curl -s -L` (sem cookies, 2 s entre requisições) devolveu HTTP 200 com 0 redirecionamentos HTTP para a home e as categorias. Esse HTML, porém, é uma página `noscript` com `meta http-equiv="refresh"` para `/gz/webdevice/config?go=...`, constatada pelo revisor. Por isso o curl **só** é usado como evidência de status HTTP: ele não prova que a página real renderiza nem detecta redirecionamentos feitos por JavaScript.

## 2. Busca (`bus-1` … `bus-6`)

**Critério:** 1 termo genérico por categoria escolhida, sem filtros, no padrão `https://lista.mercadolivre.com.br/<termo>` (minúsculas, sem acentos, uma palavra). O termo é o nome genérico de um tipo de produto típico da categoria. É uma escolha de julgamento do grupo, registrada aqui para transparência. `url_reserva` fica **vazia**, porque URLs de busca não são substituídas durante a coleta (design §8).

| Slot | Categoria | Termo |
|---|---|---|
| `bus-1` | Celulares e Telefones | `celular` |
| `bus-2` | Casa e Móveis | `sofa` |
| `bus-3` | Eletrodomésticos | `geladeira` |
| `bus-4` | Esportes e Fitness | `bicicleta` |
| `bus-5` | Ferramentas | `furadeira` |
| `bus-6` | Construção | `cimento` |

`host` = `lista.mercadolivre.com.br`, pelo padrão da URL. **As páginas de busca não foram abertas pelo agente no navegador** (decisão do coordenador; ver seção 5).

**Evidência de que a busca abre sem login no PSI:** em 18/11/2026, às 16h15 BRT, o coordenador rodou o PageSpeed Insights (pagespeed.web.dev, perfil celular, Lighthouse 13.6.0) para `https://lista.mercadolivre.com.br/celular`. O Lighthouse renderizou a página de resultados real (lista de celulares com preços, com um banner "Abra o app"), e não um CAPTCHA. Também havia dados de campo (CrUX) para a URL. Os outros 5 termos não foram testados no PSI.

## 3. Produto (`pro-1` … `pro-6`) — PENDENTE (preenchimento manual)

**Critério:** o 1º item da lista "Mais vendidos" de cada uma das 6 categorias (`url`), com o 2º item da mesma lista como `url_reserva`.

**Por que está pendente:** em 17/11/2026, as listas ranqueadas `https://www.mercadolivre.com.br/mais-vendidos/MLB<id>` levaram o navegador do agente a uma tela de CAPTCHA (`/captcha/wall`) duas vezes. O CAPTCHA não foi contornado. A página-índice `https://www.mercadolivre.com.br/mais-vendidos` abriu, mas seus carrosséis misturam itens "BLACK FRIDAY"/"OFERTA IMPERDÍVEL", não são o ranking e não incluem todas as 6 categorias. Por isso não foram usados.

IDs de categoria vistos nos links "Ver mais" da página-índice em 17/11/2026: Celulares e Telefones = `MLB1051`, Eletrodomésticos = `MLB5726`, Esportes e Fitness = `MLB1276`, Ferramentas = `MLB263532`. IDs de Casa e Móveis e de Construção: **não encontrados** (não aparecem na página-índice; procurar como no passo 2 abaixo).

**Passo a passo para o integrante A (navegador comum, sem login):**

1. Abrir `https://www.mercadolivre.com.br/mais-vendidos` em janela anônima (sem login).
2. Para cada categoria (`pro-1` Celulares e Telefones, `pro-2` Casa e Móveis, `pro-3` Eletrodomésticos, `pro-4` Esportes e Fitness, `pro-5` Ferramentas, `pro-6` Construção), abrir a lista ranqueada da categoria: pelo link "Ver mais" da seção correspondente, ou pelo link "Mais vendidos" na página da categoria (`/c/<slug>`), ou pelo filtro de categoria da própria página. A lista correta mostra os itens numerados (1º, 2º, …) e tem URL `.../mais-vendidos/MLB<id>`. Se aparecer CAPTCHA, resolvê-lo manualmente.
3. Clicar no **1º item** e copiar a URL **sem os parâmetros** após `?` e `#` → coluna `url`.
4. Voltar, clicar no **2º item** e copiar a URL da mesma forma → coluna `url_reserva`.
5. `mlb_id`: o ID MLB do 1º item gravado **exatamente como aparece na URL do anúncio, com ou sem hífen**. Exemplos: `produto.mercadolivre.com.br/MLB-1234567890-...` → `MLB-1234567890`; `www.mercadolivre.com.br/.../p/MLB12345678` → `MLB12345678`. Não normalizar (não tirar nem pôr hífen). O coletor (#9) troca o slot para a reserva quando o `final_url` não contém o `mlb_id` em 2 execuções seguidas, e essa busca é literal.
6. `host`: o host da barra de endereço **depois** que a página do 1º item terminar de carregar (finalUrl), ex.: `www.mercadolivre.com.br` ou `produto.mercadolivre.com.br`.
7. Conferir em janela anônima que as duas URLs abrem sem login.
8. Substituir os `PENDENTE` da linha em `config/urls.csv`. Manter `data_selecao` como a data real do preenchimento e anotar aqui (seção 6) a data, a hora e o ID da categoria (`MLB<id>`) de cada lista usada.
9. Commit com `Refs #5` (ou `Closes #5` se fechar a issue). Fazer isso **antes do início da coleta** (18/11, 20h07).

## 4. Home (`home`)

`https://www.mercadolivre.com.br/`, tipo `home`, sem reserva. Conferida no navegador pelo mesmo método da seção 1: `location.href` = `https://www.mercadolivre.com.br/`. É referência descritiva e não entra nos testes de tipo de página (§5.6).

## 5. Observações, riscos e notas de validade

- **Bloqueio de cliente automatizado (risco/observação).** Em 17/11/2026, sem login:
  - `curl -L` para `https://lista.mercadolivre.com.br/<termo>` (6 termos testados) terminou em `https://www.mercadolivre.com.br/gz/account-verification?go=...` (valor de `url_effective` do curl);
  - no Chrome controlado pelo agente, `lista.mercadolivre.com.br/celular` e `/mais-vendidos/MLB1051` terminaram em `/captcha/wall` (`location.href` após carregar, título "Segurança — Mercado Livre").

  O teste do PSI de 18/11 (seção 2) mostra que o Lighthouse do PSI recebeu a página real. Ainda assim, o coletor (issue #8) deve detectar bloqueio em cada medição (ex.: `finalUrl` contendo `captcha` ou `account-verification`, ou título "Segurança — Mercado Livre") e descartar ou marcar essas linhas.
- **Diferença de nível na hierarquia (validade de construto).** `cat-1` (Celulares e Telefones) é uma **subcategoria** de Tecnologia, enquanto `cat-2` … `cat-6` são categorias raiz do menu. As páginas `/c/` usam o mesmo modelo, mas uma subcategoria pode ter menos conteúdo ou outra composição, o que afeta o LCP e as auditorias. Isso enfraquece a ideia de que as 6 URLs representam igualmente "a página de categoria" e deve entrar em `docs/ameacas.md` (construto). Mitigação na análise: comparar `cat-1` com as demais na descritiva por URL e relatar se ela destoar.
- **Campanha sazonal na URL de categoria (validade de construto).** Em 18/11, `/c/esportes-e-fitness` exibiu título e `<h1>` "Projeto Verão": a mesma URL serve uma página de campanha. O conteúdo das páginas `/c/` pode mudar durante a coleta (Black Friday), então o título registrado em cada medição deve ser acompanhado.
- **Banner "Abra o app" (validade de construto).** No perfil móvel, a busca exibe um banner de convite para o app. Ele faz parte do que o usuário móvel recebe, mas pode afetar o LCP e as auditorias de acessibilidade. Registrar isso na seção de ameaças à validade (construto).
- **Período promocional.** Em 17/11/2026 o site já exibia selos "BLACK FRIDAY". A seleção de produtos depende do ranking do dia, e o ranking muda com as promoções.
- **robots.txt:** a checagem destas URLs contra o `robots.txt` é feita na issue #6 (ética).

## 6. Registro do preenchimento manual dos produtos

| Slot | Data/hora | Lista usada (`MLB<id>`) | Observações |
|---|---|---|---|
| `pro-1` | PENDENTE | `MLB1051` (a confirmar) | |
| `pro-2` | PENDENTE | não encontrado | |
| `pro-3` | PENDENTE | `MLB5726` (a confirmar) | |
| `pro-4` | PENDENTE | `MLB1276` (a confirmar) | |
| `pro-5` | PENDENTE | `MLB263532` (a confirmar) | |
| `pro-6` | PENDENTE | não encontrado | |
