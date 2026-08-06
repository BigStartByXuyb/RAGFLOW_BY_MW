# 前端调试实战:用 F12 把"按钮"和"后端接口"串起来

> 以「创建智能体」为例,教你怎么定位任意按钮触发的后端接口。
> 截图在 `screenshots/` 目录,是我在你本地页面(http://localhost:9222)实操录的。

前端技术栈:**Vite + React 18 + TypeScript**,数据层 `axios`(封装在 `next-request.ts`)+ `@tanstack/react-query`。

---

## 核心心法:两个视角结合

| 视角 | 工具 | 回答什么 |
|---|---|---|
| **运行时** | F12 → Network | 点了按钮到底发了什么 HTTP 请求(URL/参数/返回) |
| **静态** | 编辑器全局搜 | 这个 URL 在源码哪里、哪个按钮触发的 |

**F12 只能告诉你"发了什么请求",告诉不了你"哪行代码发的"。** 必须拿 F12 里看到的 URL 回代码里搜,两头一对,链路就通了。

---

## 一个最重要的认知:不是每个按钮都发请求

这次实操最直接的证据(下面网络记录是真的):

```
进入 Agent 页        → GET /api/v1/agents        ← 发请求(加载列表)
点 [+] 展开菜单       → (无请求)                   ← 纯前端
点 "Create from blank" 弹窗 → (无请求)             ← 纯前端
填名字               → (无请求)                   ← 纯前端
点 [Confirm] 提交     → POST /api/v1/agents        ← 这里才发请求!
                     → GET /api/v1/agents(自动刷新列表)
```

**只有"提交/保存/查询/删除"这类操作才真正调后端**,展开菜单、弹窗、填表都只是切换前端 UI 状态。所以调试时别急着在每个点击上找请求,盯住"提交"那一下。

---

## 实操步骤(配截图)

### 步骤 0:打开 Network 面板,准备好
1. 在页面按 **F12**
2. 切到 **Network(网络)** 标签
3. 点顶部 **Fetch/XHR** 过滤器(只看接口,滤掉图片/JS/CSS)
4. 点 **🚫 清空**,让列表干净
5. (可选)勾上 **Preserve log(保留日志)**,防止页面跳转后记录被清

### 步骤 1:进入 Agent 页面
`screenshots/01-agent-page.png` — 顶部导航 **Agent** 进来,能看到 "Create from blank"(从空白创建)按钮。
此时 Network 里有 `GET /api/v1/agents`(加载列表)。

### 步骤 2:点 "Create from blank" → 弹出对话框
`screenshots/02-create-dialog.png` — 弹出 "Create" 对话框(选类型 + 填名称)。
**注意看 Network:没有新请求。** 这一步纯前端。

### 步骤 3:填名字
`screenshots/03-filled-name.png` — 输入 "我的测试智能体"。仍然无请求。

### 步骤 4:点 Confirm → 真正发请求
`screenshots/04-created.png` — 创建成功,列表出现新智能体。
**Network 里蹦出关键请求 `POST /api/v1/agents`。** 就是它!

---

## 步骤 5:看请求细节(F12 里点开那条 POST)

在 Network 里点开 `POST /api/v1/agents`,看这几个子标签:

**General(常规)**
```
Request URL:    http://localhost:9222/api/v1/agents
Request Method: POST
Status Code:    200 OK
```

**Headers → Request Headers(请求头)**
```
authorization: IjE4MWY...(你登录后的 token,每个请求自动带)
content-type:  application/json
```
> 这个 `authorization` 头就是鉴权。它是 `next-request.ts` 的拦截器自动加的,不用你手写。

**Payload(载荷 / 请求体)** — 你发给后端的数据:
```json
{
  "title": "我的测试智能体",
  "dsl": { "graph": {...}, "components": { "begin": {...} }, "globals": {...} },
  "canvas_category": "agent_canvas"
}
```

**Response(响应)** — 后端返回:
```json
{
  "code": 0,
  "data": { "id": "804ee9b6...", "title": "我的测试智能体", "dsl": {...}, ... },
  "message": "success"
}
```
> `code: 0` = 成功(RAGFlow 约定 0 成功,非 0 报错)。`data.id` 是新建智能体的 ID。

---

## 步骤 6:反查源码 —— 从 URL 找到前端调用链

拿到 URL `/api/v1/agents`,在编辑器里**全局搜 `createAgent`**,命中 `web/src/utils/api.ts:326`:
```typescript
createAgent: `${restAPIv1}/agents`,   // = /api/v1/agents
```
顺藤摸瓜,完整链路(已核实,可逐行对照):

```
[+] 按钮(展开菜单,无请求)          pages/agents/index.tsx:131
  └─ "Create from blank" onClick     index.tsx:138  showCreatingModal
       └─ 弹出创建对话框              index.tsx:261  <CreateAgentDialog>
            └─ 表单                   create-agent-form.tsx
   [Confirm] 提交按钮 ★发请求        create-agent-form.tsx:144  data-testid="agent-save"
     └─ onSubmit → onOk(data)        create-agent-form.tsx:110
        └─ handleCreateAgentOrPipeline   hooks/use-create-agent.ts:18
           └─ setAgent(...)                    :21
              └─ useSetAgent(useMutation)  hooks/use-agent-request.ts:447  ← react-query
                 └─ agentService.createAgent    :476
                    └─ methods 登记            services/agent-service.ts:39
                       └─ URL 常量            utils/api.ts:326  (/api/v1/agents)
                          └─ axios 发出        utils/next-request.ts:79 + 拦截器 :85/:109
```

前端 5 层记牢:**页面(pages)→ 数据 hook(hooks, react-query)→ service(services)→ request 封装(utils/next-request)→ URL 常量(utils/api.ts)**。

---

## 步骤 7:接后端 —— URL 拿去后端搜

`POST /api/v1/agents` → 去 `api/apps/restful_apis/agent_api.py` 搜路由,就能找到后端处理函数。这样**前端 F12 → 后端源码**整条打通。
(后端导航见 [python-api.md](python-api.md)。)

---

## 附:一个更省事的定位技巧 —— React DevTools

装浏览器扩展 **React Developer Tools**(Chrome 商店免费),F12 会多出 **Components** 标签:
1. 点面板左上角**选择箭头**
2. 点页面上任意按钮
3. 右侧直接显示这个按钮属于哪个 React 组件、它的 props/state

配合上面的文件路径,就能"指哪查哪"定位任意按钮的源码。

---

## 可复用的通用套路(任何功能都适用)

| 步骤 | 做什么 |
|---|---|
| 1 | F12 → Network → 勾 Fetch/XHR → 清空 |
| 2 | 操作按钮,看哪一下蹦出请求,记下 URL(如 `/api/v1/xxx`) |
| 3 | 看 Payload / Response,搞清参数和返回 |
| 4 | 编辑器搜这个 URL(先搜 `utils/api.ts`)→ 找到前端调用链 |
| 5 | URL 拿去 `api/apps/restful_apis/` 搜 → 找到后端处理 |

关键提醒:F12 里的 URL 是相对路径 `/api/v1/xxx`(没有域名),因为 `next-request.ts` 没配 baseURL,靠 Vite 的 dev proxy 转发到后端。
