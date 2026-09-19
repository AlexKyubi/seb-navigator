# Changelog

Для другого агента/разработчика: краткая хронология изменений сайта. Подробный
разбор данных справочника (не входит в этот репозиторий — источник в `Data/`,
которая в `.gitignore`) смотрите в комментариях коммитов `git log` и в
локальном файле `Data/spravochnikSEB_CHANGELOG.md`, если он у вас есть.

## 2026-09-19

- **Каталог**: добавлены товары из Mechta.kz, не имевшие пары в Sulpak-справочнике.
  Товар теперь может иметь `sulpakArticle` и/или `mechtaArticle` (оба поля в
  `dist/data/idx-7f2ae1.bin`, каждое nullable). Внутренний ключ `article` —
  Sulpak-артикул как раньше (не менять формат, иначе сломается история продаж в
  IndexedDB пользователей), либо `M<mechtaArticle>` для товаров без Sulpak-кода.
  Mechta-коды zero-pad до 5 цифр (как на самом mechta.kz).
- **UI карточки**: артикулы (`S:`/`M:`) — отдельные чипы между категорией и
  названием товара (было: бейдж поверх фото, перекрывал картинку). Двойной
  тап/клик по чипу открывает страницу ретейлера в новой вкладке:
  `sulpak.kz/g/<артикул>` / `mechta.kz/search/?q=<артикул>`.
- **Каталог отдаётся обфусцированным** — `dist/data/idx-7f2ae1.bin`, не
  `catalog.json`. Это XOR+base64, **не шифрование** (ключ в `dist/assets/core.js`
  публично), защищает только от прямого/наивного просмотра ссылки. Собирается
  скриптом `scripts/build_app_data.py`. Не публиковать читаемый `catalog.json`
  снова — `scripts/verify_security.cjs` теперь это проверяет.
- **Favicon**: добавлен на все 4 страницы (раньше отсутствовал совсем).
- **Публикация**: сайт живёт на GitHub Pages, деплой автоматический по пушу в
  `main` через `.github/workflows/pages.yml` — руками собирать `dist/` не нужно.
  Домен: `sebkz.alexkyubi.com` (CNAME в Squarespace DNS → `alexkyubi.github.io.`),
  запасной адрес `alexkyubi.github.io/seb-navigator/`.
- Для `git push` использовать HTTPS remote (`gh auth git-credential`) — SSH
  (`git@github.com`) в некоторых рабочих средах зависает на порту 22.

## Правила при любой правке dist/

1. Изменили `dist/*.js`, `dist/*.html` или `dist/data/*` → поднять `CACHE` в
   `dist/sw.js`, иначе обновление не подхватится у пользователей с уже
   установленным PWA.
2. Прогнать `node scripts/verify_security.cjs` и
   `node scripts/verify_app.cjs "<файл комиссий>.xlsx"` перед пушем.
3. `modelKeys` в `dist/data/idx-7f2ae1.bin` — общее поле для поиска на фронте
   **и** для сопоставления комиссий (`buildRelation()` в `core.js`). Не класть
   туда голые числовые артикулы (sulpakArticle/mechtaArticle) — коллизия с
   чужим Comm.Code молча привяжет неверную ставку. Поиск по этим кодам и так
   работает — `catalog.js` читает поля `sulpakArticle`/`mechtaArticle` напрямую.
