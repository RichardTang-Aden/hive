# GCU Browser Automation Guide

## When to Use GCU Nodes

Use `node_type="gcu"` when:
- The user's workflow requires **navigating real websites** (scraping, form-filling, social media interaction, testing web UIs)
- The task involves **dynamic/JS-rendered pages** that `web_scrape` cannot handle (SPAs, infinite scroll, login-gated content)
- The agent needs to **interact with a website** — clicking, typing, scrolling, selecting, uploading files

Do NOT use GCU for:
- Static content that `web_scrape` handles fine
- API-accessible data (use the API directly)
- PDF/file processing
- Anything that doesn't require a browser UI

## What GCU Nodes Are

- `node_type="gcu"` — a declarative enhancement over `event_loop`
- Framework auto-prepends browser best-practices system prompt
- Framework auto-includes all 31 browser tools from `gcu-tools` MCP server
- Same underlying `EventLoopNode` class — no new imports needed
- `tools=[]` is correct — tools are auto-populated at runtime

## GCU Architecture Pattern

GCU nodes are **subagents** — invoked via `delegate_to_sub_agent()`, not connected via edges.

### How async delegation works
- Parent calls `delegate_to_sub_agent(agent_id="...", task="...")` → returns **immediately** (non-blocking)
- Parent stays available to the user while the subagent works in the background
- Subagent completion/failure injects an event into the parent's conversation automatically
- If the subagent hits a blocker (auth wall, CAPTCHA), it calls `report_to_parent(message="...", wait_for_response=true)` → parent receives a help-request event and relays it to the user
- Parent uses `respond_to_subagent(agent_id, message)` to send the user's answer back to the blocked subagent
- If a subagent appears stuck (no events for 5 minutes), parent receives a stall notification and can use `cancel_subagent(agent_id)` to kill it

### Key rules
- Parent node declares `sub_agents=["gcu-node-id"]`
- GCU nodes: `max_node_visits=1`, `client_facing=False`
- GCU nodes return structured JSON via `set_output("result", ...)`
- The parent must **NOT** poll `check_subagent_status` in a loop — events arrive automatically

## GCU Node Definition Template

```python
gcu_browser_node = NodeSpec(
    id="gcu-browser-worker",
    name="Browser Worker",
    description="Browser subagent that does X.",
    node_type="gcu",
    client_facing=False,
    max_node_visits=1,
    input_keys=[],
    output_keys=["result"],
    tools=[],  # Auto-populated with all browser tools
    system_prompt="""\
You are a browser agent. Your job: [specific task].

## Workflow
1. browser_start (only if no browser is running yet)
2. browser_open(url=TARGET_URL) — note the returned targetId
3. browser_snapshot to read the page
4. [task-specific steps]
5. set_output("result", JSON)

## If blocked
If you encounter a login wall, CAPTCHA, paywall, or any blocker you cannot
resolve yourself, call report_to_parent(message="describe what you see",
wait_for_response=true). The parent will relay your message to the user and
send back their response so you can continue.

## Output format
set_output("result", JSON) with:
- [field]: [type and description]
""",
)
```

## Parent Node Template (orchestrating GCU subagents)

```python
orchestrator_node = NodeSpec(
    id="orchestrator",
    ...
    node_type="event_loop",
    sub_agents=["gcu-browser-worker"],
    system_prompt="""\
...
## Delegating to browser sub-agents

Call delegate_to_sub_agent to launch a browser worker. This returns immediately —
you are NOT blocked. Continue talking to the user while the sub-agent works.

You will receive automatic notifications when:
- The sub-agent completes (success or failure)
- The sub-agent needs help (auth wall, CAPTCHA, etc.)
- The sub-agent appears stuck (5-minute timeout)

Do NOT call check_subagent_status in a loop. Just wait for events.

If a sub-agent needs help, relay the message to the user, get their response,
then call respond_to_subagent(agent_id="...", message="user's response").

NEVER tell a sub-agent to log in, authenticate, or bypass an auth wall.
Always relay auth blockers to the user and let THEM decide what to do.

If a sub-agent is stuck, inform the user and use cancel_subagent(agent_id="...")
if they want to abort.

Example delegation:
delegate_to_sub_agent(
    agent_id="gcu-browser-worker",
    task="Navigate to [URL]. Do [specific task]. Return JSON with [fields]."
)
...
""",
    tools=[],  # Orchestrator doesn't need browser tools
)
```

## mcp_servers.json with GCU

```json
{
  "hive-tools": { ... },
  "gcu-tools": {
    "transport": "stdio",
    "command": "uv",
    "args": ["run", "python", "-m", "gcu.server", "--stdio"],
    "cwd": "../../tools",
    "description": "GCU tools for browser automation"
  }
}
```

Note: `gcu-tools` is auto-added if any node uses `node_type="gcu"`, but including it explicitly is fine.

## GCU System Prompt Best Practices

Key rules to bake into GCU node prompts:

- Prefer `browser_snapshot` over `browser_get_text("body")` — compact accessibility tree vs 100KB+ raw HTML
- Always `browser_wait` after navigation
- Use large scroll amounts (~2000-5000) for lazy-loaded content
- For spillover files, use `run_command` with grep, not `read_file`
- If auth wall detected, call `report_to_parent(message="...", wait_for_response=true)` — don't attempt login
- Keep tool calls per turn ≤10
- Tab isolation: when browser is already running, use `browser_open(background=true)` and pass `target_id` to every call

## GCU Anti-Patterns

- Using `browser_screenshot` to read text (use `browser_snapshot`)
- Re-navigating after scrolling (resets scroll position)
- Attempting login on auth walls (subagent must escalate via `report_to_parent`)
- Parent telling subagent to "proceed with login" instead of relaying the blocker to the user
- Forgetting `target_id` in multi-tab scenarios
- Putting browser tools directly on `event_loop` nodes instead of using GCU subagent pattern
- Making GCU nodes `client_facing=True` (they should be autonomous subagents)
- Polling `check_subagent_status` in a loop (events arrive automatically)
