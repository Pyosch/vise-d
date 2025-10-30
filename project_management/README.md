# VISE-D Project Management

This folder contains project planning, tracking, and documentation materials for the VISE-D project development process.

## 📁 Folder Structure

```
project_management/
├── README.md                          # This file - overview and navigation
├── original_proposal/                 # Original project proposal documents
│   ├── pdf_content.txt               # Extracted text from Anlage 8.2
│   └── extract_pdf.py                # Script used for extraction
├── phase_7/                          # Phase 7 (Tariff Design Studio) specific materials
│   ├── implementation_guide.md       # Detailed implementation guide
│   ├── task_checklist.md            # Detailed task tracking checklist
│   ├── issue_templates/              # GitHub issue templates for Phase 7
│   │   ├── package_structure.md
│   │   ├── tou_tariff.md
│   │   ├── rtp_tariff.md
│   │   ├── grid_fee.md
│   │   └── ui_component.md
│   ├── copilot_prompts/              # Reusable Copilot prompts
│   │   ├── class_creation.md
│   │   ├── test_generation.md
│   │   ├── ui_integration.md
│   │   └── documentation.md
│   └── meeting_notes/                # Decision logs and progress notes
│       └── 2025-10-29_phase7_planning.md
└── docs_archive/                     # Archive of superseded documentation
```

## 🗂️ Key Documents

### Active Planning
- **Main Roadmap**: `../roadmap.md` - Comprehensive project roadmap with all phases
- **Phase 7 Guide**: `../docs/github_copilot_workspace_guide.md` - GitHub Copilot Workspace setup guide
- **Phase 7 Checklist**: `phase_7/task_checklist.md` - Detailed task breakdown and progress tracking

### Historical Reference
- **Original Proposal**: `original_proposal/pdf_content.txt` - VISE-D Anlage 8.2 (German)
- **Market Model Research**: See `../roadmap.md` Section "Archived Reference: Alternative Market Models Considered"

## 🎯 Current Phase: Phase 7 - Tariff Design Studio

**Status**: Planning complete, ready for implementation  
**Duration**: 7 months (est.)  
**Tasks**: 69 deliverables across 4 implementation phases

**Quick Links**:
- Implementation guide: `phase_7/implementation_guide.md`
- Task checklist: `phase_7/task_checklist.md`
- Issue templates: `phase_7/issue_templates/`
- Copilot prompts: `phase_7/copilot_prompts/`

## 📋 Using This Folder

### For Daily Work
1. Check `phase_7/task_checklist.md` for current task status
2. Use issue templates from `phase_7/issue_templates/` to create GitHub issues
3. Reference prompts in `phase_7/copilot_prompts/` when working with Copilot
4. Update meeting notes in `phase_7/meeting_notes/` after decisions

### For New Team Members
1. Read main `../roadmap.md` for project overview
2. Review `original_proposal/pdf_content.txt` for project context
3. Study `../docs/github_copilot_workspace_guide.md` for development workflow
4. Check `phase_7/implementation_guide.md` for current phase details

### For GitHub Issue Creation
```powershell
# Example: Create issue for TOUTariff implementation
# 1. Copy template
Get-Content "project_management\phase_7\issue_templates\tou_tariff.md"

# 2. Create issue on GitHub using the template
# 3. Link to GitHub Project board
# 4. Update task_checklist.md when complete
```

## 🔄 Maintenance

### When Starting a New Phase
1. Create `phase_X/` folder
2. Copy structure from `phase_7/`
3. Update this README with new phase links
4. Archive completed phase materials in `docs_archive/` if needed

### Weekly Review
- [ ] Update `phase_7/task_checklist.md` with completed tasks
- [ ] Add meeting notes to `phase_7/meeting_notes/`
- [ ] Review GitHub issues against checklist
- [ ] Update main roadmap.md if scope changes

## 📝 Document Templates

Templates are available in subdirectories:
- **Issue Templates**: `phase_7/issue_templates/*.md`
- **Copilot Prompts**: `phase_7/copilot_prompts/*.md`
- **Meeting Notes**: `phase_7/meeting_notes/*.md` (see existing for format)

## 🔗 External Links

- **GitHub Repository**: https://github.com/Pyosch/vise-d
- **GitHub Project Board**: (To be created - see github_copilot_workspace_guide.md Step 8)
- **GitHub Issues**: https://github.com/Pyosch/vise-d/issues

## 📧 Contact

For questions about project management structure or documentation, refer to:
- Main roadmap: `../roadmap.md`
- Development guide: `../docs/github_copilot_workspace_guide.md`
