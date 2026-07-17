import unittest
from pathlib import Path


WORKFLOW = (
    Path(__file__).parents[1]
    / ".github"
    / "workflows"
    / "build-node-android.yml"
)


class WorkflowTest(unittest.TestCase):
    def test_main_push_and_manual_builds_have_versions(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("  push:\n    branches:\n      - main\n", text)
        self.assertIn("  workflow_dispatch:\n", text)
        self.assertIn("NODE_VERSION: ${{ inputs.node_version || '22.23.1' }}", text)
        self.assertIn("ANDROID_API: ${{ inputs.android_api || '26' }}", text)
        self.assertIn("name: node-${{ env.NODE_VERSION }}-android-arm64-v8a", text)
        self.assertIn("retention-days: 14", text)


if __name__ == "__main__":
    unittest.main()
