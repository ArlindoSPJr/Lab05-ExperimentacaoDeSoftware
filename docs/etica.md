# Ética da coleta: robots.txt, termos de uso e regras do estudo (issue #6)

Este documento registra o que o estudo pode e não pode acessar no Mercado Livre (ML) e as regras éticas da coleta. Ele cobre o item "Ética" do design (§ "Coleta", `docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`) e a issue `#A-5` de `docs/superpowers/plans/2026-11-16-issues-ondas.md`. O coletor (issues #8 a #10) e o documento final (#20) usam este arquivo como referência.

- **Data do registro:** 18/11/2026.
- **Quem acessou:** o agente da tarefa, pelo Chrome do integrante, **sem login**, com 1 requisição por host e ≥ 2 s entre requisições.
- **URLs verificadas:** `config/urls.csv` da issue #5 (13 URLs preenchidas e 6 produtos `PENDENTE`).

## Resumo

| Pergunta | Resposta |
|---|---|
| Alguma URL de `config/urls.csv` é proibida pelo `robots.txt` (`User-agent: *`)? | **Não.** As 6 categorias, as 6 buscas e a home são permitidas (seção 2). |
| Os padrões das URLs de produto são permitidos? | **Sim**, os dois padrões, desde que sem query string e sem sufixos proibidos (seção 3). |
| Há regra que nomeia o PageSpeed Insights / Lighthouse? | **Não.** Vale o grupo `User-agent: *` (seção 4). |
| Achados que pedem decisão do coordenador | (1) Os 3 hosts bloqueiam `ClaudeBot` e `Claude-User` em `/`, e a seleção da #5 foi feita com um agente Claude no navegador. (2) O caminho `/mais-vendidos/MLB`, usado para escolher os produtos, é proibido para `*`. (3) O texto atual dos Termos e Condições do ML não foi lido no site oficial (seções 5 e 6.1). |

## 1. robots.txt de cada host

### 1.1 Método e registro de acesso

1ª tentativa, por `curl` (User-Agent padrão do curl, 1 requisição por host, 2 s entre elas): os 3 hosts responderam **HTTP 403**, com `Server: CloudFront` e `X-Cache: Error from cloudfront`. O corpo era uma página HTML de erro, idêntica nos 3 hosts (mesmo MD5), e não o `robots.txt`. O bloqueio não foi contornado (não se trocou o User-Agent).

2ª tentativa, pelo Chrome do integrante (o mesmo navegador da issue #5), abrindo `https://<host>/robots.txt`. O texto foi lido com `document.body.innerText` e o status com `performance.getEntriesByType('navigation')[0].responseStatus`.

| Host | URL | Status HTTP | Data e hora do acesso (UTC) | Horário de Brasília (UTC−3) | Tamanho do texto |
|---|---|---|---|---|---|
| `www.mercadolivre.com.br` | `https://www.mercadolivre.com.br/robots.txt` | 200 | 2026-11-18T19:40:02Z | 18/11/2026 16:40 | 2.947 caracteres |
| `lista.mercadolivre.com.br` | `https://lista.mercadolivre.com.br/robots.txt` | 200 | 2026-11-18T19:40:12Z | 18/11/2026 16:40 | 11.522 caracteres |
| `produto.mercadolivre.com.br` | `https://produto.mercadolivre.com.br/robots.txt` | 200 | 2026-11-18T19:40:25Z | 18/11/2026 16:40 | 3.848 caracteres |

Tentativas de `curl` (403): 2026-11-18T19:39:12Z (`www.`), 19:39:14Z (`lista.`), 19:39:17Z (`produto.`).

Leitura das regras pela RFC 9309 (Robots Exclusion Protocol). Fonte: <https://www.rfc-editor.org/rfc/rfc9309> (acesso em 18/11/2026).
- O crawler usa os grupos que nomeiam o seu User-Agent; se houver mais de um, as regras deles são combinadas. Se nenhum grupo o nomeia, ele usa `User-agent: *` (§2.2.1).
- `*` casa 0 ou mais caracteres e `$` marca o fim do padrão (§2.2.3).
- A comparação de caminhos "SHOULD be case sensitive" (§2.2.2).
- Entre `Allow` e `Disallow` vale a regra que casa mais octetos. Em empate, o `Allow` (§2.2.2).

### 1.2 Estrutura comum aos 3 hosts

Os 3 arquivos começam com o mesmo grupo de bloqueio total:

```
User-agent: Amazonbot
User-agent: PerplexityBot
User-agent: Perplexity-User
User-agent: ClaudeBot
User-agent: Claude-User
User-agent: GPTBot
User-agent: ChatGPT-User
Disallow: /
```

Depois vêm um grupo de redes sociais com `Allow: /` (no `www.`: FacebookExternalHit, FacebookBot, Twitterbot, LinkedInBot; no `produto.`: Twitterbot; no `lista.` não há esse grupo), um grupo `Bingbot` com `Crawl-delay: 5` e, por fim, o grupo `User-agent: *`. Nenhum grupo nomeia `Googlebot`, `Google-InspectionTool`, `Lighthouse`, `Chrome-Lighthouse` ou `HeadlessChrome`.

### 1.3 `www.mercadolivre.com.br` — trecho relevante do grupo `User-agent: *`

Regras que tocam caminhos do estudo ou caminhos próximos (o grupo completo tem 48 `Disallow` e 4 `Allow`):

```
User-agent: *
Disallow: /HOME/
Disallow: /gz/webdevice/config
Disallow: /noindex/
Disallow: /navigation/
Disallow: /*itemid
Disallow: /*/jm/item
Disallow: /recommendations*
Disallow: /*attributes=
Disallow: /*quantity=
Disallow: /home/recommendations
Disallow: /*.js
Disallow: /*redirect_to_reviews=
Disallow: /*/p/MLB*/s
Disallow: /*/p/MLB*/seller-info
Disallow: /*/p/MLB*/specifications
Disallow: /gz/
Disallow: /mais-vendidos/MLB
Disallow: /ofertas?
Allow: /home/recommendations/pom
```

Não há regra para `/`, para `/c/` nem para `/<slug>/p/MLB<id>` sem sufixo. As outras linhas do grupo tratam de `/gz/...`, `/perfil/...`, `/pagina/*_id`, `/tienda/*_id`, `/clips?short_id=`, `/anuncie`, `/blog/cg-*`, APIs internas e similares. Nenhuma casa as URLs do estudo.

### 1.4 `lista.mercadolivre.com.br` — trecho relevante do grupo `User-agent: *`

O grupo é longo (o arquivo inteiro tem 11.522 caracteres). As regras que importam para uma busca `/<termo>` são de três tipos:

- **Filtros e ordenações na URL** (o estudo não usa nenhum): `*_Discount_`, `/*_OrderId_`, `/*_FilterId_`, `/*_BestSellers_`, `/*_PriceRange_`, `/*_PriceMin_`, `/*_PriceMax_`, `*_ItemTypeID_`, `*_DisplayType_`, `/*_Desde_`, `/*_NoIndex_True`, `/*_SortsToApply`, `/*_FiltersToApply`, `/*variation=`, entre outras.
- **Termos que contêm certas palavras ou fragmentos**: nomes de marcas e serviços (`/*mercadolivre`, `/*mercado-livre`, `/*mercadopago`, `/*merca`, `*www.`, `*http`, `*mail.`), prefixos de anúncio (`*/mlb-`, `*/mla-`, …) e uma lista de termos de conteúdo adulto (ex.: `/*-sexo-`, `/*-porno$`).
- **Seções e extensões**: `/adultos/*`, `/pagina/*`, `/supermercado/*`, `/farmacia/*`, `/e/`, `/loja/*/lista`, `/*.html`, `/*.php`, `/*.js`, `/*.css`, `/*.jpg`, `/*.gif`.

Destaque, por casar com termos curtos: `Disallow: /*merca` bloqueia qualquer caminho que contenha `merca` (ex.: "mercado", "mercearia"). Nenhum dos 6 termos do estudo contém esse fragmento.

### 1.5 `produto.mercadolivre.com.br` — trecho relevante do grupo `User-agent: *`

```
User-agent: *
Disallow: /*?show=
Disallow: /*?tool=
Disallow: /*?searchVariation=
Disallow: /*?attribute=
Disallow: /*?redirectedFromChild
Disallow: /*?redirectedFromSimilar
Disallow: /*?redirectedFromSearch
Disallow: /*?no_index
Disallow: /*?noIndex
Disallow: /www
Disallow: /url
Disallow: /vip/
Disallow: /VIP/
Disallow: /jm
Disallow: /info
Disallow: /content
Disallow: /questions
Disallow: /descriptions
Disallow: /checkout
Disallow: /location
Disallow: /email
Disallow: /tags
Disallow: /login/
Disallow: /*.html
Disallow: /*.js
Allow: /*_JM$
```

As regras sem `*` (ex.: `/info`, `/jm`, `/content`) são **prefixos**: só casam caminhos que começam assim. Um caminho de anúncio começa com `/MLB-`, então não é afetado. A linha `Allow: /*_JM$` libera explicitamente os caminhos que terminam em `_JM`, a terminação usual dos anúncios (`.../MLB-<id>-<slug>-_JM`).

## 2. Conferência das URLs de `config/urls.csv`

Todas as URLs foram comparadas com o grupo `User-agent: *` do seu host (seção 4).

| slot_id | url | Regra aplicável | Permitido? |
|---|---|---|---|
| `cat-1` | `https://www.mercadolivre.com.br/c/celulares-e-telefones` | `www.`: nenhuma regra casa `/c/...` | Sim |
| `cat-2` | `https://www.mercadolivre.com.br/c/casa-moveis-e-decoracao` | `www.`: nenhuma regra casa `/c/...` | Sim |
| `cat-3` | `https://www.mercadolivre.com.br/c/eletrodomesticos` | `www.`: nenhuma regra casa `/c/...` | Sim |
| `cat-4` | `https://www.mercadolivre.com.br/c/esportes-e-fitness` | `www.`: nenhuma regra casa `/c/...` | Sim |
| `cat-5` | `https://www.mercadolivre.com.br/c/ferramentas` | `www.`: nenhuma regra casa `/c/...` | Sim |
| `cat-6` | `https://www.mercadolivre.com.br/c/construcao` | `www.`: nenhuma regra casa `/c/...` | Sim |
| `bus-1` | `https://lista.mercadolivre.com.br/celular` | `lista.`: sem filtro `_..._`, sem fragmento proibido (`merca`, `mlb-`, `www`, `http`, termos adultos), sem extensão | Sim |
| `bus-2` | `https://lista.mercadolivre.com.br/sofa` | idem | Sim |
| `bus-3` | `https://lista.mercadolivre.com.br/geladeira` | idem | Sim |
| `bus-4` | `https://lista.mercadolivre.com.br/bicicleta` | idem | Sim |
| `bus-5` | `https://lista.mercadolivre.com.br/furadeira` | idem | Sim |
| `bus-6` | `https://lista.mercadolivre.com.br/cimento` | idem | Sim |
| `home` | `https://www.mercadolivre.com.br/` | `www.`: nenhuma regra casa `/` (`/HOME/` difere em maiúsculas e exige a barra final) | Sim |
| `pro-1` … `pro-6` | `PENDENTE` | ver seção 3 | Padrões permitidos; checar cada URL real |

Conclusão: **nenhuma URL preenchida de `config/urls.csv` é proibida**, e o arquivo não foi alterado.

**Redirecionamentos para caminhos proibidos.** Os destinos de bloqueio vistos na issue #5 ficam em caminhos **proibidos**: `/gz/account-verification` está sob `Disallow: /gz/`, e a página `noscript` aponta para `/gz/webdevice/config`. O estudo não pede esses caminhos. Se o PSI terminar num deles, a medição é descartada (seção 7, regra 7).

## 3. URLs de produto (pendentes): padrões e regra de checagem

| Padrão | Exemplo de forma | Regras que poderiam casar | Permitido? |
|---|---|---|---|
| `https://www.mercadolivre.com.br/<slug>/p/MLB<id>` | `/<slug>/p/MLB12345678` | `/*/p/MLB*/s`, `/*/p/MLB*/seller-info`, `/*/p/MLB*/specifications` exigem um segmento **depois** do ID (`/s…`, `/seller-info`, `/specifications`); `/*itemid`, `/*attributes=`, `/*quantity=`, `/*redirect_to_reviews=` só casam com esses textos no caminho ou na query | **Sim**, sem query string e sem segmento após o ID |
| `https://produto.mercadolivre.com.br/MLB-<id>-<slug>` (geralmente terminando em `-_JM`) | `/MLB-1234567890-<slug>-_JM` | Os prefixos (`/jm`, `/info`, `/www`, …) não casam um caminho que começa com `/MLB-`; `/*?show=` e os demais exigem query string; `/*.html` exige `.html`. Se terminar em `_JM`, a linha `Allow: /*_JM$` libera explicitamente | **Sim**, sem query string |

**Regra de checagem para quando as URLs reais forem preenchidas** (integrante A, antes do commit em `config/urls.csv`):

1. A URL deve estar **sem** `?…` e `#…` (o passo 3 de `docs/urls-selecao.md` já pede isso). Uma query string pode ativar `/*?show=`, `/*?attribute=`, `/*attributes=`, `/*quantity=`, `/*redirect_to_reviews=` e similares.
2. No `www.`: o caminho deve terminar no ID (`.../p/MLB<dígitos>`), sem segmento depois dele, e não pode conter `itemid`, `/jm/item` nem `.js`.
3. No `produto.`: o caminho deve começar com `/MLB-` e não pode conter `.html` nem `.js`.
4. Conferir as URLs de `url_reserva` com os mesmos passos.
5. Se alguma URL falhar: usar a URL canônica do mesmo anúncio sem o trecho que casa a regra. Se não houver, a próxima posição da lista "Mais vendidos". Registrar a troca em `docs/urls-selecao.md` (seção 6).

Para checar automaticamente, usar um verificador que implemente `*` e `$` como na RFC 9309. A documentação do `urllib.robotparser` do Python não diz se ele suporta `*` e `$` nos caminhos. Fonte: <https://docs.python.org/3/library/urllib.robotparser.html> (acesso em 18/11/2026). Por isso, não confiar nele sem testar antes com as regras desta seção (ex.: `/*/p/MLB*/s` e `Allow: /*_JM$`). Na dúvida, fazer a checagem manual dos passos 1 a 4.

**Atenção à seleção dos produtos:** o grupo `*` do `www.` tem `Disallow: /mais-vendidos/MLB`, ou seja, as listas ranqueadas usadas como critério na #5 são proibidas para robôs. O `robots.txt` rege robôs, não pessoas navegando. Por isso o preenchimento **manual**, por um integrante num navegador comum, é compatível com ele. Essas páginas **não** podem ser abertas por script, agente ou pelo PSI. Elas também não entram na coleta, pois só servem para escolher os produtos.

## 4. Quem acessa as páginas na coleta: o PSI, e não um crawler nosso

Na coleta, o nosso código (GitHub Actions) **não** baixa páginas do ML. Ele chama a API do PageSpeed Insights (`googleapis.com`), e é a infraestrutura do Google que carrega a URL:

- A documentação do PSI diz que ele "uses Lighthouse to analyze the given URL in a simulated environment" e que "PageSpeed also runs in a Google datacenter". Fonte: <https://developers.google.com/speed/docs/insights/v5/about> (acesso em 18/11/2026).
- O exemplo de resposta da documentação traz um `userAgent` com `HeadlessChrome`. Fonte: <https://developers.google.com/speed/docs/insights/v5/get-started> (acesso em 18/11/2026). O User-Agent exato usado em produção **não está documentado** nessas páginas. O coletor deve registrar `lighthouseResult.environment` e `userAgent` de cada resposta.

**Discussão.** O `robots.txt` é um pedido aos *crawlers*, isto é, programas que descobrem e seguem links sozinhos. A RFC 9309 o define como regras para "crawlers" e diz que as regras "are not a form of access authorization". Fonte: <https://www.rfc-editor.org/rfc/rfc9309> (acesso em 18/11/2026). O PSI não rastreia: para cada chamada ele faz **1 carregamento** da URL que nós indicamos, como um navegador faria, sem seguir links. Ainda assim, quem decide o que é carregado e quando somos nós, então o grupo adota a postura conservadora:

1. **Tratamos o PSI como se fosse um robô nosso** e só pedimos URLs permitidas pelo grupo `User-agent: *` dos 3 hosts (seções 2 e 3). Como nenhum grupo nomeia o Lighthouse ou um agente do Google, vale o `*`.
2. **Respeitamos o espírito do `Crawl-delay`.** O único `Crawl-delay` é o do `Bingbot` (5 s), que não se aplica a nós. Mesmo assim, as chamadas são **sequenciais**, com ≥ 1 s entre elas. São 38 carregamentos por rodada (19 URLs × 2 perfis) a cada ~2 h, o que dá menos de 0,005 req/s de média por site.
3. **Não pedimos caminhos proibidos**, nem mesmo os de bloqueio (`/gz/…`, `/captcha/…`). Se o PSI for redirecionado para um deles, a medição é descartada.

## 5. Achado: bloqueio a `ClaudeBot` e `Claude-User`

Os 3 hosts têm `Disallow: /` para `ClaudeBot` e `Claude-User`, além de outros agentes de IA (seção 1.2). Segundo a Anthropic, "Claude-User supports Claude AI users": quando alguém faz uma pergunta ao Claude, ele pode acessar sites com esse agente. A mesma página diz que os bots da Anthropic respeitam o `robots.txt`. Fonte: <https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler> (acesso em 18/11/2026).

Consequências para o estudo:

- **Coleta:** não é afetada. Quem carrega as páginas é o PSI, não o Claude (seção 4).
- **Seleção das URLs (#5) e esta tarefa:** um agente Claude abriu páginas do ML pelo Chrome do integrante em 17 e 18/11/2026. O Chrome envia o User-Agent normal do navegador, e não `Claude-User`. Mesmo assim, o pedido do site, no espírito, alcança esse uso. Páginas abertas pelo agente: home, as 6 `/c/…`, `/mais-vendidos`, `/mais-vendidos/MLB1051` (CAPTCHA), `lista.mercadolivre.com.br/celular` (CAPTCHA), os 3 `robots.txt` nesta tarefa, e ainda alguns `curl`/`fetch` de status.
- **Decisão adotada nesta tarefa:** depois dos 3 `robots.txt`, nenhuma outra página do ML foi aberta pelo agente. Por isso os Termos e Condições do ML não foram lidos no site oficial (seção 6.1).
- **Recomendação ao grupo (a decidir pelo coordenador):** daqui em diante, nenhum agente de IA abre páginas do ML. O que for preciso ver no site (produtos, termos) é feito por um integrante, à mão. O documento final declara esse uso nas limitações, com as datas acima.

## 6. Termos de uso

### 6.1 Mercado Livre — Termos e Condições Gerais de Uso do Site

- **Link oficial (a ler pelo integrante A):** <https://www.mercadolivre.com.br/ajuda/Termos-e-condicoes-gerais-de-uso_1409>. Esse endereço aparece citado no plano eleitoral 2026 do ML, publicado pela Justiça Eleitoral: <https://www.justicaeleitoral.jus.br/desinformacao/arquivos/plano-de-conformidade/mercado-livreversao-publica-plano-de-contingencia-e-conformidade-eleitoral-2026.pdf> (resultado de busca de 18/11/2026; PDF não aberto).
- **Situação: texto NÃO lido na fonte oficial.** A página não foi aberta pelo agente por causa do bloqueio a `Claude-User` (seção 5). **Nenhuma cláusula é citada aqui como confirmada.**
- **Onde se procurou (18/11/2026):** duas buscas na web ("Termos e condições gerais de uso do site" Mercado Livre robôs; variações com "spiders", "mecanismo", "dispositivo"). O texto integral dos termos gerais não apareceu nos resultados. Indícios **não confirmados**, a verificar no texto oficial:
  - uma resposta pública do ML no Reclame Aqui cita a "cláusula 10" dos Termos Gerais para justificar a suspensão de uma conta por "bloqueio por robô": <https://www.reclameaqui.com.br/mercado-livre/bloqueio-por-robo_Ikex9FvV-yMJygy2/> (página não aberta);
  - um vídeo curto afirma que uma cláusula que proíbe bots, scrapers e agentes de IA entrou em vigor em 15/10/2026: <https://www.youtube.com/shorts/da1bBex7lJE> (não verificado; um vídeo não é fonte primária).
- **Termos para desenvolvedores do ML (contexto, não se aplicam diretamente):** segundo o resumo da busca, a cláusula 7.6 dos Termos e Condições de Uso do programa de desenvolvedores proíbe usar "robôs, harvesters, spiders, scraping ou outra tecnologia" para acessar o conteúdo ou o site: <https://developers.mercadolivre.com.br/pt_br/termos-e-condicoes> (página não aberta; o texto vem do resumo do buscador). O estudo não usa a API do ML.
- **Avaliação provisória:** o estudo não usa conta, não faz login, não raspa nem guarda o conteúdo dos anúncios (preços, vendedores) para reuso. Ele mede só o desempenho e a acessibilidade da página, por 1 carregamento do PSI a cada ~2 h por URL. Isso **parece** fora do alvo de uma cláusula contra robôs e scraping, mas é uma interpretação do grupo. **Pendência:** o integrante A lê os termos oficiais, cola aqui o número e o texto curto das cláusulas sobre robôs, automação e coleta de conteúdo, com a data de acesso, e revê esta avaliação. Se os termos proibirem expressamente a medição automatizada por terceiros, o grupo leva isso ao professor antes de seguir.

### 6.2 PageSpeed Insights API e Termos de Serviço das Google APIs

Fontes lidas em 18/11/2026:

- **PSI API, "Get started":** <https://developers.google.com/speed/docs/insights/v5/get-started>. Para uso automatizado é preciso uma chave de API, criada na página de credenciais do Google Cloud (<https://console.cloud.google.com/apis/credentials>) e enviada no parâmetro `key=`. A página diz que a chave "is safe for embedding in URLs" (no sentido de codificação da URL; ver o item sobre confidencialidade abaixo). A página **não traz números de cota** nem link para termos próprios. Ela avisa ainda que o Google planeja descontinuar os dados do CrUX nessa API, recomendando a CrUX API; isso é um risco para a H5, a registrar nas ameaças.
- **Google APIs Terms of Service** (última modificação indicada: 9/11/2021): <https://developers.google.com/terms>. Pontos aplicáveis:
  - **§2(d), "API Limitations":** o Google "sets and enforces limits on your use of the APIs", e o usuário concorda em não tentar contornar esses limites ("will not attempt to circumvent"). → Uma chave, chamadas sequenciais, sem rodízio de chaves ou projetos para ganhar cota.
  - **§2(b), "Compliance with Law, Third Party Rights…":** cumprir a lei, os direitos de terceiros e os demais termos do Google. → Respeitar os termos do ML e o `robots.txt`.
  - **§3(b) e §3(d), segurança e privacidade:** proteger informações de usuários e cumprir as leis de privacidade. → Não coletamos dados pessoais (seção 7).
  - **§4(b), "Confidential Matters":** "You will keep your credentials confidential", e credenciais não podem ficar em projetos de código aberto. → A chave fica só no secret `PSI_API_KEY` do GitHub e nunca no código, nos logs ou nos JSON versionados.
  - **§5(e), "Prohibitions on Content":** proíbe raspar, montar bases ou fazer cópias permanentes do *conteúdo devolvido pelas APIs* sem permissão do dono ou da lei. → **Ponto de atenção:** o estudo versiona o JSON do Lighthouse (sem as capturas de tela) como dado bruto de pesquisa. O grupo entende que métricas e resultados de auditoria são o propósito da API, e não "conteúdo" de terceiros, e por isso remove as capturas de tela, que são o conteúdo visual do ML. Isso é uma interpretação, a registrar como limitação.
- **Cota numérica da PSI API: não encontrada em fonte oficial.** Nenhuma das páginas lidas dá números, e nenhuma remete a uma página de cotas. Sites de terceiros citam 25.000 consultas/dia por projeto, com limites por minuto divergentes (ex.: <https://unlighthouse.dev/learn-lighthouse/pagespeed-insights-api/rate-limits>, acesso em 18/11/2026). Esse número **não** é tratado como oficial. A cota real deve ser lida no console do projeto (APIs e serviços → PageSpeed Insights API → Cotas) e registrada aqui. Para referência: 38 chamadas a cada ~2 h dão cerca de 456 por dia.

## 7. Regras do estudo (obrigatórias para o coletor e para os integrantes)

1. **No máximo 1 requisição por segundo** a qualquer host, seja ao PSI ou a site do ML. O coletor faz as chamadas em sequência, com pausa mínima de 1 s entre o fim de uma e o início da próxima, e sem paralelismo. Cada URL é carregada 2 vezes por rodada (móvel e desktop), e as rodadas são espaçadas de ~2 h.
2. **Sem teste de carga ou estresse** em sistemas do ML ou do Google. O volume é fixo (38 chamadas por rodada) e não aumenta para "ganhar amostra".
3. **Sem login.** Nenhuma URL exige conta, e nenhuma credencial do ML é usada.
4. **Sem dados pessoais.** As URLs são páginas públicas de catálogo. Não se guardam nomes, avaliações, perguntas de usuários, dados de vendedores pessoa física, nem a localização de entrega (já ocultada na captura da #5).
5. **Capturas de tela removidas antes de versionar.** O coletor apaga do JSON do Lighthouse as auditorias `final-screenshot`, `screenshot-thumbnails` e `full-page-screenshot` antes de compactar e fazer commit, conforme o design ("JSON bruto"). Isso tira imagens que podem mostrar nomes de pessoas ou conteúdo de terceiros e reduz o tamanho. Um teste do coletor (#8 a #10) deve verificar que nenhuma dessas chaves sobra.
6. **Chave só no secret `PSI_API_KEY`.** Ela nunca entra em código, configuração versionada ou logs. A URL de chamada com `key=` não é impressa. A chave não é compartilhada fora do grupo (Google APIs ToS §4(b)).
7. **Detecção de bloqueio e descarte.** Se o `finalUrl` da resposta contiver `/captcha/` (ex.: `/captcha/wall`) ou `/gz/account-verification`, ou se o título for "Segurança — Mercado Livre", a medição é marcada como `bloqueada` e **excluída da análise**, contando só como dado de disponibilidade. O CAPTCHA nunca é resolvido nem contornado por script, e não se trocam User-Agent, IP ou chave para fugir do bloqueio. Se o bloqueio persistir, a coleta daquela URL é suspensa e o coordenador é avisado.
8. **Respeito ao `robots.txt`.** Só são pedidas URLs permitidas pelo grupo `User-agent: *` do host (seções 2 e 3). Toda URL nova ou trocada (inclusive as reservas de produto) passa pela checagem da seção 3 antes do commit. Tipos de página proibidos são excluídos do estudo, conforme o design.
9. **Páginas proibidas só à mão.** `/mais-vendidos/MLB…` e outros caminhos proibidos só podem ser abertos por um integrante, num navegador comum, para selecionar URLs. Nunca por script, agente ou PSI.
10. **Agentes de IA:** recomendação da seção 5, a decidir pelo coordenador.

## 8. Pendências

| Item | Responsável | Antes de |
|---|---|---|
| Ler os Termos e Condições Gerais do ML no link oficial e registrar as cláusulas sobre robôs, automação e coleta (número, trecho curto, data) na seção 6.1 | Integrante A | Início da coleta |
| Checar as 12 URLs de produto (`url` e `url_reserva`) pela regra da seção 3 | Integrante A | Commit dos produtos em `config/urls.csv` |
| Ler a cota da PSI API no console do projeto e registrar na seção 6.2 | Quem criou a chave | Início da coleta |
| Decidir a política sobre agentes de IA (seção 5) e declarar o uso já feito nas limitações | Coordenador / grupo | Documento final (#20) |
