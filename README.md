# 港人北上出行多因素相关性分析
主样本：2023-02-06 至 2026-10-31。原始数据放在 `data/raw/`，处理后的数据放在 `data/processed/`。

## 当前阶段
- [x] 项目目录、依赖清单与密钥忽略规则
- [x] 共用 HTTP 工具 `src/fetch_utils.py`
- [ ] 全员建立虚拟环境并安装依赖
- [ ] 各成员确认取数、清洗模块的输入输出格式
- [ ] 全组在 2026-11-08 前完成数据冻结

## 本地启动
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/fetch_utils.py
```

Windows PowerShell 激活命令：`.venv\\Scripts\\Activate.ps1`。

密钥只放在本地 `.env`，禁止提交；`.env` 已列入 `.gitignore`。项目当前没有创建 `.env`，也没有保存任何密钥。

