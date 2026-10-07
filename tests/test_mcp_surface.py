"""MCP server exposes the six public-data tools."""

from cmg_agent import mcp_server


def test_six_tools_registered():
    tool_fns = [
        mcp_server.fda_search_labels,
        mcp_server.fda_get_label_section,
        mcp_server.trials_search,
        mcp_server.trials_get,
        mcp_server.cms_ncd_search,
        mcp_server.cms_ncd_get,
    ]
    assert len(tool_fns) == 6
    for fn in tool_fns:
        assert callable(fn)
        assert fn.__doc__


def test_server_metadata():
    assert mcp_server.server.name == "cmg"
