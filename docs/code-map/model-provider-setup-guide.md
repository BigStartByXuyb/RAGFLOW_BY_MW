# RAGFlow 模型配置实战指南(DeepSeek + 千问 Embedding)

> 本文档记录在本地 RAGFlow(http://localhost:9222)配置 LLM 和 Embedding 模型的完整流程,
> 以及排查"验证失败 / 模型列表为空"两个真实坑的过程。截图在 `screenshots/model-*.png`。

配置入口:右上角头像 → **模型提供商**(URL `/user-setting/model`)。

---

## 一、关键概念:三步缺一不可

在模型设置页,一个厂商要真正可用,必须走完**三步**:

| 步骤 | 动作 | 对应接口 | 不做的后果 |
|---|---|---|---|
| 1. 验证 | 单模型点"验证" | `POST /providers/{p}/connection` | 只是测 key 能不能用,**不保存** |
| 2. 保存实例 | 填实例名 + 点"保存" | `POST /providers/{p}/instances` | **key 和模型不会落库** |
| 3. 落库确认 | — | `GET /models` 返回该模型 | 下拉框才有可选项 |

**最容易漏的是第 2 步的"实例名称"**:它是必填项,空着点"保存"**不会发请求**(前端表单校验拦截),表现为"点了没反应"。

---

## 二、两个真实坑(务必知道)

### 坑 1:模型验证成功,但"保存实例"报 `102 No valid response received`

**现象**:单个模型点"验证"返回成功,但点"保存"整个实例时报:
```
102 Fail to access model(DeepSeek/deepseek-v4-flash).No valid response received
```

**真正根因(实测抓包确认)**:不是 key 错、不是网络、不是超时,而是——
**浏览器自动填充把你的登录邮箱填进了一个隐藏的 `group_id` 字段**。

前端 `buildApiKeyValue`(`web/src/pages/user-setting/setting-model/instance-card/hooks.tsx:46`)会检查表单里的
`group_id`/`api_version`/`provider_order`(`API_KEY_NESTED_FIELDS`,`interface.ts:128`)。
这几个字段本是给 MiniMax/Azure 等厂商用的。一旦有值,它会把 api_key 包成:
```json
"api_key": { "api_key": "sk-xxx", "group_id": "1046393883@qq.com" }
```
后端 `provider_api_service.py:483` 对非字符串 key 做 `json.dumps`,于是发给 DeepSeek 的 key 变成
`{"api_key":"sk-xxx","group_id":"...@qq.com"}` 整串 → DeepSeek 返回 **401 Authentication Fails**
(后端日志里 key 显示为 `****om"}`)→ 被统一归为 `No valid response received`。

**为什么"验证"成功、"保存"失败?** 两条路径组装 payload 的方式不同:验证直传干净字符串,保存走了 `buildApiKeyValue` 包装。

**解决**:保存前清掉被污染的 group_id。在浏览器 F12 Console 里执行:
```js
document.querySelectorAll('input').forEach(el=>{
  if((el.name||'').toLowerCase().includes('group_id') && el.value){
    const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
    s.call(el,''); el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));
  }
});
```
> 治本建议:给浏览器地址栏这个站点**关闭自动填充**,或用无痕窗口配置模型,避免邮箱/密码乱填进隐藏字段。
> 同样的自动填充还会把 API Key 填进登录页密码框,登录前也要留意。

### 坑 2:模型验证成功、实例也存了,但"设置默认模型"下拉框空

**原因**:同坑 1——实例其实没存进库(`GET /providers/{p}/instances` 返回 `data:[]`,`has_instance:false`),
所以 `GET /models` 为空 → 下拉"暂无数据"。把坑 1 解决、实例真正落库后,下拉就有了。

### 坑 3(千问特有):厂商预置 150 个模型,保存极慢/易失败

千问(Tongyi-Qianwen)默认挂 150 个模型(LLM 112、Embedding 3、TTS 19...)。
保存时后端会**逐个串行验证**,你没开通的会各等一个超时(默认 10s,可调),累积极慢。
> 后端判定逻辑(`provider_api_service.py:866-869`):**只要有任意一个模型验证通过,整体保存就算成功**。
> 但为了快,最佳做法是**只保留你要用的模型**(见下方千问流程)。

---

## 三、DeepSeek(LLM)配置流程

DeepSeek 只有两个模型:`deepseek-v4-flash`、`deepseek-v4-pro`(**没有 V3**,别填 v3 名字)。
base_url:`https://api.deepseek.com/v1`。详见 [[deepseek-model-config]]。

1. 模型提供商页 → 点 **DeepSeek**
2. 填 **实例名称**(如 `DeepSeek`)——必填,别漏
3. 填 **API Key**(`sk-...`)
4. **F12 Console 执行坑 1 的清理脚本**,清掉被自动填充污染的 group_id
5. (可选)单独点某模型"验证"确认 key 可用 → 应返回成功
6. 点右上角 **保存** → `POST /instances` 返回 `{"code":0}` 即成功
7. 到 **设置默认模型** → LLM 选 `deepseek-v4-flash`(快、便宜、日常够用)

---

## 四、千问 Embedding(text-embedding-v3)配置流程

⚠️ **Embedding 模型选定后不能换**:知识库建好后向量维度绑死,换 embedding 要重建所有知识库。本次用 `text-embedding-v3`。

1. 模型提供商页 → 点 **Tongyi-Qianwen**
2. 填 **实例名称**(如 `Qwen`)
3. 填 **API Key**(千问/DashScope 的 `sk-...` key)
4. **F12 Console 执行坑 1 的清理脚本**清 group_id
5. 因为默认 150 个模型太多:点搜索框旁的 **"批量移除当前模型"**(进入选择模式,所有模型变为默认不选)
6. 在模型搜索框输入 `text-embedding-v3` 过滤 → 点它的 **Add** 加入实例(只加这一个)
7. 点右上角 **保存** → `POST /instances` 返回 `{"code":0}` 即成功
8. 到 **设置默认模型** → Embedding 选 `text-embedding-v3`

---

## 五、配置完成的验证

- `GET /api/v1/models` 返回已配置的模型(不再是 `[]`):应能看到 `deepseek-v4-flash`、`deepseek-v4-pro`、`text-embedding-v3`
- **设置默认模型** 下拉框:LLM 选 DeepSeek,Embedding 选 text-embedding-v3
- 截图:`screenshots/model-01-providers-configured.png`

---

## 六、附:F12 抓包定位问题的通用方法

配置类问题排查,F12 Network 是利器:
1. F12 → Network → 勾 Fetch/XHR → 清空
2. 做一个操作(如点保存),看蹦出的请求
3. 点开请求看 **Payload**(你发了什么)和 **Response**(后端返回什么)
4. 本次就是靠对比"验证"和"保存"两个请求的 Payload,发现 `api_key` 从干净字符串变成了带 group_id 的 dict,从而定位根因

（本次排查还改了后端 `LLM_TIMEOUT_SECONDS=60` 提高验证超时容忍度,但最终证明根因是 group_id 污染,与超时无关。)
