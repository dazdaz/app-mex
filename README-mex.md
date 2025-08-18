# MEX - Model EXplorer 🚀

**MEX (Model EXplorer)** is a powerful desktop application built with PyQt6 that provides a user-friendly interface for interacting with various Large Language Models (LLMs) hosted on **Google Cloud's Vertex AI platform**. It streamlines the process of sending prompts to models like **Anthropic's Claude** 🤖 and **Google's Gemini** ✨, offering a rich set of features for developers and researchers to explore and experiment with AI capabilities.

## Key Features:

*   **Multi-Model Support:** Seamlessly switch and query various LLMs available on Vertex AI, including Claude 3.7 Sonnet 🗣️, Claude 4.1 Opus 🧠, Gemini 2.5 Pro 🌟, and Gemini 2.5 Flash ⚡.
*   **Intuitive Query Interface:** Dedicated tabs for individual queries, each with its own prompt input 📝, model selection 🎯, and response display 💬.
*   **Real-time Metrics & Estimates:**
    *   Live character 📏 and approximate token 🔢 counting for both input prompts and generated responses.
    *   **Fictional pricing estimates** 💰 based on configurable token costs, providing a conceptual understanding of usage (with clear disclaimers that these are not actual Google Cloud costs! ⚠️).
*   **Query Synchronization:** An innovative "Sync queries" 🔗 feature allows users to apply the same prompt across multiple tabs simultaneously, enabling easy side-by-side comparison of different models' responses to the same input.
*   **Dynamic Theming:** Toggle between elegant dark 🌙 and light ☀️ modes to suit user preferences and reduce eye strain.
*   **Adjustable Font Sizes:** Customize the application's font size 🔍 for improved readability and accessibility.
*   **Enhanced Response Handling:**
    *   View model responses in clean, parsed text or inspect the raw JSON output 📄 for debugging and deeper analysis.
    *   Copy generated responses 📋 or entire prompts to the clipboard with a single click.
    *   Export responses 📥 to text or JSON files for external use or archival.
*   **Robust Backend Interaction:** Utilizes `requests` for secure communication with Vertex AI, handling authentication via `google.auth` credentials 🔐 and managing streaming responses. API calls are performed in background threads 🏃‍♂️ to ensure a responsive user interface.
*   **User-Friendly Onboarding:** Prompts the user for their Google Cloud Project ID ☁️ on first launch, with sensible defaults and a clear disclaimer about the application's non-official status and fictional pricing.

MEX aims to be a valuable tool 🛠️ for anyone working with Vertex AI, simplifying model interaction and offering insights into token usage and (simulated) cost implications in a visually appealing and highly functional desktop environment. ✨
