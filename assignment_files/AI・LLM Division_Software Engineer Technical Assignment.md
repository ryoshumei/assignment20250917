### **Backend Task**

There is a workflow application as described in the "Application Structure" section below.  
 Please extend the backend of this application to meet the following requirements:

---

#### **Requirements**

* **Persist data using a datastore**  
   The application should no longer store data in memory but instead persist it using an appropriate data storage mechanism.

* **Make workflow execution asynchronous**  
   Workflow execution should be processed asynchronously.

* **Implement `NodeType.GENERATIVE_AI`**

  * Extend the backend to allow the use of an LLM (Large Language Model) API.

  * The prompt and model should be user-configurable.

  * You may add additional parameters as needed.

* **Implement `NodeType.FORMATTER`**

  * Extend the application so that it can format a given piece of text.

  * Examples: convert to lowercase, convert to uppercase, transform from half-width to full-width characters.

  * Users should be able to configure the formatting rules.

* **Allow PDF file uploads** and implement `NodeType.EXTRACT_TEXT` to extract text from uploaded files.

* **(Optional)**: Support directed acyclic graph (DAG) structure

  * Enable workflows with multiple inputs and outputs.

* **(Optional)**: Add an AI agent node to workflow execution

  * You may define what an "AI agent" means in your implementation.

  * Common capabilities include:

    * Planning tasks based on a given objective

    * Determining which tools to use

    * Automatically recognizing when the task is complete

  ---

  #### **Deliverables**

* **Source code**  
   (e.g., GitHub repository or downloadable ZIP file)

* **README**

  * Setup and launch instructions

  * API endpoint specifications

  * Any special considerations

* **(Optional)**: Tests and instructions on how to run them

  ---

  #### **Notes**

* You may implement this from scratch using any language or framework.

* You are allowed to use generative AI tools for development. If you do, please describe how you used them.

* Please provide a breakdown of how much time each task took.
**Application Structure**

```
.
├── server
│   ├── main.py            # Entry point for FastAPI
│   ├── models.py          # Pydantic models, enums, etc.
│   ├── schemas.py         # Request/response schemas
│   └── requirements.txt   # Python dependencies
└── client
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts     # Vite config for running React
    └── src
        ├── App.tsx        # Root React component
        ├── api.ts         # API wrapper for backend communication
        └── types.ts       # TypeScript type definitions
```

