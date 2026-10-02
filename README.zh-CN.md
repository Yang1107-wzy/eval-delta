# Eval Delta · 评测回归对比

[English](README.md) · [发布包](https://github.com/Yang1107-wzy/eval-delta/releases)

按样本 ID 对齐两次评测，找出平均分掩盖的个别退步。输入已有 JSONL 结果，不调用模型、不需要 API Key，也不需要 pandas 或后台服务。

![真实示例输出的排版展示](docs/demo.svg)

## 安装

Python 3.10+，没有运行时第三方依赖。当前通过 GitHub 发布，未发布到 PyPI。

```sh
python -m pip install "git+https://github.com/Yang1107-wzy/eval-delta.git@v1.0.0"
eval-delta --version
```

## 快速体验

```sh
git clone https://github.com/Yang1107-wzy/eval-delta.git
cd eval-delta
python -m pip install .
eval-delta examples/baseline.jsonl examples/candidate.jsonl --metric error:lower --metric latency_ms:lower
eval-delta examples/baseline.jsonl examples/improved.jsonl --metric error:lower --format json
eval-delta examples/baseline.jsonl examples/candidate.jsonl --metric error:lower --format markdown > comparison.md
```

第一个示例平均误差改善，但 `sample-b` 退步，因此返回 1。第二个全部改善，返回 0。两份文件的记录顺序可以不同。

## 输入约定

```json
{"id":"sample-a","error":4.0,"latency_ms":100}
{"id":"sample-b","error":2.0,"latency_ms":80}
```

每行一个对象，支持 `.gz`。ID 必须是唯一的非空字符串或整数；整数 `1` 和字符串 `"1"` 是不同样本，布尔值无效。通过 `--id-key case_id` 指定其他 ID 字段。

两次运行中的每行都必须包含指定指标，且是有限数值。缺失指标、字符串数值、布尔值、重复属性、空行、无效 JSON 均返回 2。小数必须能经 Python float 往返而不丢十进制位；`1e-400` 等下溢和超高精度小数会被拒绝，避免悄悄改变评测结论。

## 判定规则

`--metric error:lower` 表示越小越好，`--metric accuracy:higher` 表示越大越好，可重复声明不同顶层指标。

对于越小越好的指标，`candidate - baseline > tolerance` 算退步；越大越好则反向。绝对变化不超过容差算不变。`--tolerance` 默认 0，是每条样本的绝对容差，单位与指标相同。同次调用所有指标共用容差；不同单位需要不同容差时请分开运行。

通过条件：ID 集完全一致、至少一条配对样本、任一指标都没有样本退步。缺失或新增 ID 也判失败。平均值仅基于配对样本；均值提升不会抵消个别退步。这是确定性回归门槛，不是统计显著性检验。

## 输出与退出码

```sh
eval-delta baseline.jsonl candidate.jsonl --metric error:lower --format json > delta.json
```

JSON 报告包含 `schema_version: 1`、配对数、两次记录数、缺失/新增 ID、各指标均值和变化、退步/改善/不变计数、退步样本及通过状态。Markdown 可放入 GitHub Actions job summary；具体工作流见英文说明。

`--max-details` 默认 100，只限制跨指标的退步细节样本，统计仍覆盖全部配对记录。样本按指标参数顺序与编码后的 ID 排序，不按退步程度排名；零配对时均值为 null。

| 退出码 | 含义 |
| --- | --- |
| 0 | 比较通过 |
| 1 | 有退步、ID 集变化或无配对样本 |
| 2 | 用法、文件或数据无效 |

## 边界

同时将两次评测载入内存，面向中小规模评测。样本判定使用接受数值表示的精确有理数差，报告中的差值和均值使用浮点计算；溢出拒绝处理。不验证实验协议、数据来源、置信区间、嵌套指标或 API。输入不修改，报告写入 stdout。需要完整模型评测平台可使用 [Promptfoo](https://github.com/promptfoo/promptfoo)；本项目是独立的小型结果对比工具。

MIT 许可，提供跨平台 CI、测试和合成示例。
