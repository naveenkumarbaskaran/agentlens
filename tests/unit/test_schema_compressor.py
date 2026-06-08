from agentlens.integrations.mcp.compressor import SchemaCompressor


def test_compress_removes_verbose_description():
    schema = {
        "name": "read_file",
        "description": "Read the full contents of a file from the filesystem. " * 20,
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "file path"}},
        },
    }
    compressor = SchemaCompressor(max_description_chars=100)
    compressed = compressor.compress(schema)
    assert len(compressed["description"]) <= 100


def test_compress_preserves_input_schema():
    schema = {
        "name": "read_file",
        "description": "Short description",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    }
    compressor = SchemaCompressor(max_description_chars=100)
    compressed = compressor.compress(schema)
    assert compressed["inputSchema"]["required"] == ["path"]
