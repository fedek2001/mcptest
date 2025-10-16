from mcp.server.fastmcp import FastMCP

# Instancia MCP para todo tu “servidor”
mcp = FastMCP("vercel-mcp-python")

# ---- TOOLS (ejemplos) ----
@mcp.tool()
def reverse(text: str) -> str:
    """Invierte un string."""
    return text[::-1]

@mcp.tool()
def add(a: float, b: float) -> float:
    """Suma dos números."""
    return a + b
