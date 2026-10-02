# 素页 Plainpage 静态官网

纯 HTML/CSS，无框架、运行时翻译服务或网络构建依赖。首页包含产品简介和完整 FAQ，每种语言另有技术支持和 App 隐私政策。

## 内容与生成

- `content/locales.json`：九语言唯一内容源；不要直接编辑生成的 HTML。
- `tools/build_site.py`：Python 标准库生成器。JSON-LD 问答与可见问答来自同一内容。
- 简中保留原 `/plainpage/`、`support.html`、`privacy.html`；其他语言为 `zh-Hant/`、`en/`、`ja/`、`ko/`、`fr/`、`es/`、`pt-BR/`、`it/` 下的同名三页，共 27 页。
- 每页有自引用 canonical、九语言双向 hreflang、指向英语同类页面的 x-default，以及保持页面类型的语言切换；无自动跳转。sitemap 列出全部 27 个 canonical URL。
- `pt-BR` 是巴西葡萄牙语，不是葡萄牙变体。网页语言不等于 App 在某个国家/地区可售，本站不声明全球可售。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/build_site.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/build_site.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

`--check` 只读检查源内容和已提交产物一致；测试覆盖 27 页链接、语言切换、hreflang/canonical、sitemap、可见 FAQ/schema 一致性、隐私正文及反馈警示覆盖。中文/英文隐私六段正文使用原始 Git 基线 `29a87949461a80ab6096565c39c2a95bb8f6777c` 的空白归一化摘要防漂移；其余语言为翻译自校，自动测试不是母语准确性或法律审查证明。

## 事实与边界

iPhone / iOS 17+ / 免费 / Safari 双扩展；广告判定使用本地模型，不上传网页内容。不保证所有广告被移除、零误删、搜索收录或答案引擎引用。隐私政策适用于 App 与扩展；主动提交到公开 GitHub Issues 的网页反馈不是 App 的数据收集功能，提交前须移除敏感信息。法国/西班牙/葡萄牙/意大利等语言入口不能作为开放地区的证明。

无项目内 robots.txt：爬虫读取 `https://alexlee2046.github.io/robots.txt`，而不是 `/plainpage/robots.txt`；本仓不管理用户站根目录。根 robots 404 或无 noindex 不证明收录。

GitHub Pages 为 legacy `main:/`；合并 main 即生产发布。当前仅准备候选 PR，不合并、不部署，不新增 CI 或监控；后续生产发布须由 lead 走已批准的发布门。
