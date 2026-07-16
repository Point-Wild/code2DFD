from core.file_interaction import grep_command, detection_comment


def test_grep_command_excludes_node_modules():
    cmd = grep_command("PublishCommand", "/repo")
    assert cmd[0] == "grep"
    assert "-rn" in cmd
    assert "--exclude-dir=node_modules" in cmd
    assert "--exclude-dir=dist" in cmd
    assert "--exclude-dir=.git" in cmd
    assert cmd[-2:] == ["PublishCommand", "/repo"]


def test_detection_comment_handles_typescript():
    assert detection_comment("sns.ts", "// a comment") is True
    assert detection_comment("sns.ts", "const x = 1;") is False
