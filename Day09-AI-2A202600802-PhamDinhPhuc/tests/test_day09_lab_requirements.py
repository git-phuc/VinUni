import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse(path: str) -> ast.Module:
    return ast.parse((ROOT / path).read_text(encoding="utf-8"))


def get_assign_name(module: ast.Module, name: str) -> ast.Assign:
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node
    raise AssertionError(f"{name} assignment not found")


def function_names(module: ast.Module) -> set[str]:
    return {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_llm_uses_openai_api_key_and_model_without_openrouter_base_url():
    source = (ROOT / "common" / "llm.py").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY" in source
    assert "OPENAI_MODEL" in source
    assert "temperature=0.3" in source
    assert "OPENROUTER_API_KEY" not in source
    assert "OPENROUTER_MODEL" not in source
    assert "openrouter.ai" not in source


def test_stage_2_adds_labor_knowledge_and_statute_tool():
    module = parse("stages/stage_2_rag_tools/main.py")
    source = (ROOT / "stages" / "stage_2_rag_tools" / "main.py").read_text(encoding="utf-8")

    assert '"id": "labor_law"' in source
    assert "Theo Bộ luật Lao động Việt Nam 2019" in source
    assert "check_statute_of_limitations" in function_names(module)

    tools_assign = get_assign_name(module, "TOOLS")
    assert isinstance(tools_assign.value, ast.List)
    tool_names = [item.id for item in tools_assign.value.elts if isinstance(item, ast.Name)]
    assert "check_statute_of_limitations" in tool_names


def test_stage_3_adds_case_law_tool_to_react_agent():
    module = parse("stages/stage_3_single_agent/main.py")

    assert "search_case_law" in function_names(module)

    tools_assign = get_assign_name(module, "TOOLS")
    assert isinstance(tools_assign.value, ast.List)
    tool_names = [item.id for item in tools_assign.value.elts if isinstance(item, ast.Name)]
    assert "search_case_law" in tool_names


def test_stage_4_adds_privacy_agent_routing_and_aggregation():
    module = parse("stages/stage_4_milti_agent/main.py")
    source = (ROOT / "stages" / "stage_4_milti_agent" / "main.py").read_text(encoding="utf-8")

    assert "needs_privacy" in source
    assert "privacy_result" in source
    assert "call_privacy_specialist" in function_names(module)
    assert all(keyword in source for keyword in ["data", "privacy", "gdpr", "dữ liệu"])
    assert "Privacy/GDPR Analysis" in source
    assert 'graph.add_node("call_privacy_specialist", call_privacy_specialist)' in source
