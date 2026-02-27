# Gumbo — Architecture & Design Document

## 1. Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI LAYER                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │  Sidebar      │  │  Main Area   │  │  Results Panel         │    │
│  │              │  │              │  │                        │    │
│  │ • New Project│  │ ┌──────────┐ │  │ • Per-tab output       │    │
│  │ • Load/Save  │  │ │  Tab 1   │ │  │ • Integrated result    │    │
│  │ • Project    │  │ │──────────│ │  │ • Export options        │    │
│  │   selector   │  │ │ Main     │ │  │                        │    │
│  │ • Integrator │  │ │ Prompt   │ │  │                        │    │
│  │   config     │  │ │──────────│ │  │                        │    │
│  │ • Run All    │  │ │ LLM pick │ │  │                        │    │
│  │              │  │ │ Tools []│ │  │                        │    │
│  │              │  │ │──────────│ │  │                        │    │
│  │              │  │ │ SubTask1 │ │  │                        │    │
│  │              │  │ │ SubTask2 │ │  │                        │    │
│  │              │  │ │  + Add   │ │  │                        │    │
│  │              │  │ └──────────┘ │  │                        │    │
│  │              │  │ [Tab2][Tab3] │  │                        │    │
│  └──────────────┘  └──────────────┘  └────────────────────────┘    │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA MODEL LAYER                            │
│                                                                     │
│  Project ──┬── SequenceTab[] ──┬── SubTask[]                       │
│            │                   │                                    │
│            │                   ├── main_prompt: str                 │
│            │                   ├── llm: str                         │
│            │                   ├── tools: list[str]                 │
│            │                   └── output: str | None               │
│            │                                                        │
│            ├── integrator_llm: str                                  │
│            ├── integrator_prompt: str                               │
│            └── final_result: str | None                             │
│                                                                     │
│  SubTask ──┬── prompt: str                                         │
│            ├── llm: str                                             │
│            ├── tools: list[str]                                     │
│            └── output: str | None                                   │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WORKFLOW ENGINE                                │
│                                                                     │
│  ┌────────────┐    ┌────────────┐    ┌──────────────────┐          │
│  │  Tab Runner │───▶│  Task      │───▶│  Integrator      │          │
│  │            │    │  Executor  │    │                  │          │
│  │ For each   │    │            │    │ Combines all tab │          │
│  │ tab in     │    │ Calls LLM  │    │ outputs using    │          │
│  │ sequence:  │    │ with tools │    │ chosen LLM or    │          │
│  │  run main  │    │ returns    │    │ program into one │          │
│  │  then subs │    │ text result│    │ final result     │          │
│  └────────────┘    └────────────┘    └──────────────────┘          │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                  │
│                                                                     │
│  ┌─────────────────┐   ┌──────────────────┐                        │
│  │  JSON File I/O  │   │  projects/       │                        │
│  │                 │   │   ├── proj1.json  │                        │
│  │ • save_project()│   │   ├── proj2.json  │                        │
│  │ • load_project()│   │   └── ...         │                        │
│  │ • list_projects│   │                   │                        │
│  └─────────────────┘   └──────────────────┘                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Data Models

### Project
| Field              | Type              | Description                                    |
|--------------------|-------------------|------------------------------------------------|
| id                 | str (UUID)        | Unique project identifier                      |
| name               | str               | Human-readable name (e.g. "Life Tracker")      |
| description        | str               | Optional project description                   |
| tabs               | list[SequenceTab] | Ordered sequence of prompt tabs                |
| integrator_llm     | str               | LLM used for final integration                 |
| integrator_prompt  | str               | Prompt template for the integrator step        |
| final_result       | str or None       | Combined output after full run                 |
| created_at         | str (ISO datetime)| Creation timestamp                             |
| updated_at         | str (ISO datetime)| Last modification timestamp                    |

### SequenceTab
| Field       | Type           | Description                                    |
|-------------|----------------|------------------------------------------------|
| id          | str (UUID)     | Unique tab identifier                          |
| title       | str            | Tab label (e.g. "Health", "Finance")           |
| main_prompt | str            | The main prompt text for this tab              |
| llm         | str            | Selected LLM for the main prompt               |
| tools       | list[str]      | Selected tools for the main prompt             |
| subtasks    | list[SubTask]  | Ordered sub-slot action items                  |
| output      | str or None    | Result after running this tab's main prompt    |
| position    | int            | Order index within the project                 |

### SubTask
| Field   | Type       | Description                                    |
|---------|------------|------------------------------------------------|
| id      | str (UUID) | Unique subtask identifier                      |
| prompt  | str        | The sub-task / action-item prompt text          |
| llm     | str        | Selected LLM for this subtask                  |
| tools   | list[str]  | Selected tools for this subtask                |
| output  | str or None| Result after running this subtask              |

## 3. High-Level Pseudocode

### Creating a Project
```
user clicks "New Project"
  → prompt for project name + description
  → project = Project(name, description)
  → add one empty SequenceTab as default
  → save to session state
  → persist to JSON
```

### Adding Tabs / Prompts / Sub-items
```
user clicks "+ Add Tab"
  → tab = SequenceTab(title="Tab N")
  → project.tabs.append(tab)
  → re-render UI with new tab

user edits main prompt textarea in a tab
  → tab.main_prompt = new_text
  → auto-save

user clicks "+ Add Sub-task" within a tab
  → subtask = SubTask(prompt="")
  → tab.subtasks.append(subtask)
  → re-render with new subtask input
```

### Selecting LLMs / Tools
```
for each tab:
  user picks LLM from dropdown (GPT-4, Claude-3, Grok, ...)
    → tab.llm = selected_value

  user checks tool checkboxes (web_search, code_exec, ...)
    → tab.tools = [checked items]

  for each subtask in tab:
    same LLM dropdown + tool checkboxes
    → subtask.llm = ...
    → subtask.tools = [...]
```

### Running Sequences
```
for tab in project.tabs (in order):
  # 1. Run main prompt
  result = execute_task(tab.main_prompt, tab.llm, tab.tools)
  tab.output = result

  # 2. Run each subtask in order, passing prior context
  context = result
  for subtask in tab.subtasks:
    sub_result = execute_task(
      subtask.prompt,
      subtask.llm,
      subtask.tools,
      context=context,
    )
    subtask.output = sub_result
    context += sub_result   # chain outputs
```

### Integrating
```
all_outputs = [tab.output for tab in project.tabs]
  + [sub.output for tab in project.tabs for sub in tab.subtasks]

final_prompt = project.integrator_prompt.format(outputs=all_outputs)
project.final_result = execute_task(
  final_prompt,
  project.integrator_llm,
  tools=[],
)
display(project.final_result)
save_project(project)
```

## 4. Dependencies

| Package      | Purpose                                       |
|--------------|-----------------------------------------------|
| streamlit    | Web UI framework                              |
| pydantic     | Data model validation and serialization       |
| requests     | HTTP calls to external LLM APIs               |
| python-dotenv| Load API keys from `.env`                     |

Install:
```bash
pip install streamlit pydantic requests python-dotenv
```
