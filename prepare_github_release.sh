#!/bin/bash

# Legacy GitHub Release Preparation Script for ABrain v1.0.0 predecessor
# This historical helper predates the hardened ABrain closure workflow.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.0.0"

echo -e "${BLUE}=== ABrain legacy v${VERSION} release preparation ===${NC}"
echo -e "${YELLOW}Warning: this script targets a historical full-stack release flow and is not the canonical hardened release path.${NC}"
echo -e "${BLUE}Project root: ${PROJECT_ROOT}${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists git; then
    echo -e "${RED}✗ Git is not installed${NC}"
    exit 1
fi

if ! command_exists gh; then
    echo -e "${YELLOW}⚠ GitHub CLI is not installed. You'll need to create the PR manually.${NC}"
    GH_CLI_AVAILABLE=false
else
    echo -e "${GREEN}✓ GitHub CLI found${NC}"
    GH_CLI_AVAILABLE=true
fi

# Check Git status
echo -e "${YELLOW}Checking Git status...${NC}"
cd "$PROJECT_ROOT"

# Ensure we're on the correct branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "feature/v1.0.0-fullstack-release" ]; then
    echo -e "${YELLOW}Switching to feature/v1.0.0-fullstack-release branch...${NC}"
    git checkout feature/v1.0.0-fullstack-release || {
        echo -e "${RED}✗ Failed to switch to release branch${NC}"
        exit 1
    }
fi

# Check if changes are staged/committed
if ! git diff --quiet; then
    echo -e "${YELLOW}Uncommitted changes detected. Staging and committing...${NC}"
    git add .
    git commit -m "🔧 Additional changes for v1.0.0 release

- Updated project dependencies and configurations
- Refined Docker and setup scripts
- Enhanced documentation and setup processes"
fi

echo -e "${GREEN}✓ Git repository is clean${NC}"

# Create release tag if it doesn't exist
if git tag -l | grep -q "^v${VERSION}$"; then
    echo -e "${GREEN}✓ Release tag v${VERSION} already exists${NC}"
else
    echo -e "${YELLOW}Creating release tag v${VERSION}...${NC}"
    git tag -a "v${VERSION}" -m "Release v${VERSION}: Full-Stack Integration

This release introduces a complete full-stack integration with:
- Modern React frontend with TypeScript and Tailwind CSS
- FastAPI backend bridge for seamless ABrain integration
- Real-time WebSocket communication
- Comprehensive dashboard and agent management
- Automated setup and testing scripts
- Docker support and containerization

Key features:
🎯 Complete full-stack solution
💻 Modern React UI with responsive design
🚀 One-click setup and deployment
🔄 Real-time communication via WebSockets
📊 System monitoring and metrics
🤖 Agent orchestration and management

See RELEASE_NOTES_v1.0.0.md for full details."
    echo -e "${GREEN}✓ Created release tag v${VERSION}${NC}"
fi

# Verify release files exist
echo -e "${YELLOW}Verifying release files...${NC}"

REQUIRED_FILES=(
    "README.md"
    "CHANGELOG.md"
    "VERSION"
    "RELEASE_NOTES_v1.0.0.md"
    "FULLSTACK_README.md"
    "server/main.py"
    "start_fullstack.sh"
    "test_system.sh"
    "status_check.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ ${file}${NC}"
    else
        echo -e "${RED}✗ Missing: ${file}${NC}"
        exit 1
    fi
done

# Create release archive (optional)
echo -e "${YELLOW}Creating release archive...${NC}"
ARCHIVE_NAME="agent-nn-v${VERSION}-release.tar.gz"

# Create a temporary directory for the release
TEMP_DIR=$(mktemp -d)
RELEASE_DIR="${TEMP_DIR}/agent-nn-v${VERSION}"

# Copy essential files for release
mkdir -p "$RELEASE_DIR"
cp -r \
    README.md \
    CHANGELOG.md \
    VERSION \
    RELEASE_NOTES_v1.0.0.md \
    FULLSTACK_README.md \
    LICENSE \
    server/ \
    frontend/agent-ui/ \
    requirements.txt \
    .env.example \
    start_fullstack.sh \
    test_system.sh \
    status_check.sh \
    docker-compose.yml \
    "$RELEASE_DIR/" 2>/dev/null || echo "Some optional files not found"

# Create the archive
tar -czf "$ARCHIVE_NAME" -C "$TEMP_DIR" "agent-nn-v${VERSION}"
echo -e "${GREEN}✓ Created release archive: ${ARCHIVE_NAME}${NC}"

# Clean up temporary directory
rm -rf "$TEMP_DIR"

# Generate release notes summary
echo -e "${YELLOW}Generating release summary...${NC}"

cat > RELEASE_SUMMARY.md << EOF
# 🚀 Agent-NN v${VERSION} Release Summary

## Quick Start
\`\`\`bash
git clone https://github.com/EcoSphereNetwork/Agent-NN.git
cd Agent-NN
bash start_fullstack.sh
\`\`\`

## Access Points
- **Frontend**: http://localhost:3001
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs

## Login Credentials
- **Email**: demo@abrain.local
- **Password**: demo

## Key Features
- 🎯 Complete full-stack solution (React + FastAPI)
- 💻 Modern React UI with TypeScript and Tailwind CSS
- 🚀 One-click setup and deployment
- 🔄 Real-time WebSocket communication
- 📊 System monitoring and metrics dashboard
- 🤖 Agent orchestration and management

## System Requirements
- Python 3.10+
- Node.js 18+
- 4+ GB RAM
- 5+ GB disk space

## What's New
- Complete frontend-backend integration
- Automated setup and testing scripts
- Real-time chat interface
- Comprehensive dashboard
- Agent and task management
- WebSocket communication

## Files in Release
- README.md - Updated with full-stack features
- CHANGELOG.md - Complete release history
- RELEASE_NOTES_v${VERSION}.md - Detailed release notes
- FULLSTACK_README.md - Comprehensive setup guide
- server/main.py - FastAPI backend bridge
- start_fullstack.sh - One-click startup script
- test_system.sh - System validation script
- status_check.sh - Real-time status monitoring

See RELEASE_NOTES_v${VERSION}.md for complete details.
EOF

echo -e "${GREEN}✓ Created release summary${NC}"

# Show next steps
echo ""
echo -e "${MAGENTA}=== Next Steps ===${NC}"
echo ""
echo -e "${BLUE}1. Push the feature branch:${NC}"
echo -e "   ${YELLOW}git push origin feature/v1.0.0-fullstack-release${NC}"
echo ""

if [ "$GH_CLI_AVAILABLE" = true ]; then
    echo -e "${BLUE}2. Create Pull Request (GitHub CLI):${NC}"
    echo -e "   ${YELLOW}gh pr create --title \"🚀 Release v${VERSION}: Full-Stack Integration\" --body-file RELEASE_SUMMARY.md --base main --head feature/v1.0.0-fullstack-release${NC}"
    echo ""
    echo -e "${BLUE}3. Create GitHub Release:${NC}"
    echo -e "   ${YELLOW}gh release create v${VERSION} ${ARCHIVE_NAME} --title \"Agent-NN v${VERSION}: Full-Stack Integration\" --notes-file RELEASE_NOTES_v${VERSION}.md --prerelease${NC}"
else
    echo -e "${BLUE}2. Create Pull Request manually:${NC}"
    echo -e "   ${YELLOW}Go to GitHub and create a PR from feature/v1.0.0-fullstack-release to main${NC}"
    echo -e "   ${YELLOW}Use RELEASE_SUMMARY.md as the PR description${NC}"
    echo ""
    echo -e "${BLUE}3. Create GitHub Release manually:${NC}"
    echo -e "   ${YELLOW}Go to GitHub Releases and create a new release${NC}"
    echo -e "   ${YELLOW}Tag: v${VERSION}${NC}"
    echo -e "   ${YELLOW}Title: Agent-NN v${VERSION}: Full-Stack Integration${NC}"
    echo -e "   ${YELLOW}Description: Use content from RELEASE_NOTES_v${VERSION}.md${NC}"
    echo -e "   ${YELLOW}Attach: ${ARCHIVE_NAME}${NC}"
fi

echo ""
echo -e "${BLUE}4. After PR is merged:${NC}"
echo -e "   ${YELLOW}git checkout main${NC}"
echo -e "   ${YELLOW}git pull origin main${NC}"
echo -e "   ${YELLOW}git push origin v${VERSION}${NC}"
echo ""

echo -e "${GREEN}=== Release Preparation Complete! ===${NC}"
echo -e "${GREEN}Archive created: ${ARCHIVE_NAME}${NC}"
echo -e "${GREEN}Release summary: RELEASE_SUMMARY.md${NC}"
echo ""
echo -e "${YELLOW}Ready to push and create PR! 🚀${NC}"

# Optional: Show current git status
echo ""
echo -e "${BLUE}Current Git Status:${NC}"
git log --oneline -5
echo ""
git status --short
