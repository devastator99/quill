# Socratic

Welcome to Socratic, a decentralized platform inspired by the Socratic method—a timeless approach to learning through questioning, dialogue, and critical thinking. Socratic harnesses the power of the Solana blockchain and a robust FastAPI backend to enable users to upload documents, engage in contextual conversations, and generate thought-provoking questions, all while fostering transparency and incentivizing participation through a token-based economy.

## Table of Contents

- [Why Socratic?](#why-socratic)
- [Features](#features)
- [Architecture](#architecture)
- [Workflow for Blockchain Interactions](#workflow-for-blockchain-interactions)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Questions?](#questions)

## Why Socratic?

Why accept knowledge at face value when you can probe deeper through inquiry? Socratic empowers users to:

- **Upload Documents**: Share PDFs, CSVs, or Markdown files, which are intelligently processed into structured chunks for analysis.
- **Ask Questions**: Engage in context-aware conversations with an AI that draws insights from your uploaded documents.
- **Explore Deeply**: Receive Socratic-style questions that challenge assumptions and spark critical reflection.
- **Participate Transparently**: Leverage Solana’s blockchain to track document uploads, queries, and token transactions securely.

Like the Socratic method, this platform encourages curiosity, critical analysis, and collaborative learning in a decentralized ecosystem.

## Features

- **Document Processing**: Upload various file types (PDF, CSV, Markdown) and let the system extract text, create intelligent chunks, and generate embeddings for semantic search.
- **Contextual Chat**: Ask questions and receive responses grounded in your uploaded documents, powered by a language model (Mistral-7B).
- **Socratic Questioning**: Automatically generate open-ended, thought-provoking questions for each document chunk to stimulate deeper understanding.
- **Blockchain Integration**: Use Solana and Anchor to manage user accounts, document uploads, and queries with a token-based system for transparency and incentives.
- **Real-Time Collaboration**: Communicate via WebSocket for real-time chat interactions.
- **Scalable Backend**: Built with FastAPI and PostgreSQL (with PGVector for embeddings), ensuring high performance and extensibility.

## Architecture

Socratic combines a powerful backend with a decentralized blockchain layer:

- **Frontend (React Native)**: Sends parameters and data to the FastAPI backend, signs transactions using a Solana wallet adapter, and displays results.
- **Backend (FastAPI)**:
  - Constructs unsigned Solana transactions for actions like document uploads and queries.
  - Verifies transaction signatures using Anchorpy , Solathon and Solana’s RPC.
  - Processes documents with LangChain for text extraction, chunking, and embedding generation.
  - Stores metadata and embeddings in PostgreSQL with PGVector.
  - Uses Celery for asynchronous task processing (e.g., generating summaries and questions).

- **Blockchain (Solana with Anchor)**:
  - Manages user accounts, document records, and query records via a Solana program.
  - Enforces token-based access for actions like uploading documents (10 tokens) and making queries (1 token).
  - Supports token purchasing, staking, and document sharing with transparent on-chain records.

## Workflow for Blockchain Interactions

1. The frontend sends action parameters (e.g., `pdf_hash`, `access_level`) to the FastAPI backend.
2. The backend constructs an unsigned transaction and returns it to the frontend.
3. The frontend signs the transaction using a wallet adapter and sends the signature back.
4. The backend verifies the signature and proceeds with the action (e.g., processes the uploaded file or answers a query).

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+ (for React Native frontend)
- Solana CLI (for blockchain interactions)
- PostgreSQL with PGVector extension
- Redis (for Celery)
- Solana wallet (e.g., Phantom) for testing on Devnet

### Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/socratic.git
   cd socratic
   ```

2. **Set Up the Backend:**

   ```bash
   #change directory to backend
   cd backend
   # activate your virtual env(optional)
   # Install Python dependencies
   pip install -r requirements.txt
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your DATABASE_URL, OPENAI_API_KEY, etc.
   # Initialize the database
   python -m models
   ```

3. **Set Up the Solana Program:**

   ```bash
   # Install Anchor
   cargo install --git https://github.com/coral-xyz/anchor anchor-cli --locked
   # Build and deploy the Solana program
   cd anchor_programs
   anchor build
   anchor deploy --provider.cluster devnet
   # Copy the generated IDL to the backend
   cp target/idl/socratic_token.json ../backend/
   ```

4. **Run the Backend:**

   ```bash
   # Start Redis and Celery
   redis-server &
   celery -A celery_worker worker --loglevel=info &
   # Start FastAPI
   uvicorn main:app --reload
   ```

5. **Set Up the Frontend:**

   ```bash
   cd frontend
   npm install
   npm start
   ```

## Configuration

### .env File:

```
DATABASE_URL=postgresql://user:password@localhost:5432/socratic
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Solana Setup:

- Ensure your Solana program is deployed to Devnet.
- Update the `PROGRAM_ID` in `main.py` with your deployed program’s ID.

## Usage

1. **Login:**

   - Use a Solana wallet to sign a message and authenticate via the `/login` endpoint.
   - Receive a JWT token for subsequent requests.

2. **Upload a Document:**

   - Send a file and parameters (e.g., `access_level`) to `/build_upload_transaction`.
   - Sign the returned transaction with your wallet.
   - Submit the signature to `/verify_and_process_upload`.
   - Check the status via `/upload_status/{upload_id}`.

3. **Chat with Context:**

   - Send a query to `/build_chat_transaction`.
   - Sign the returned transaction and submit the signature to `/verify_and_process_chat`.
   - Receive a response grounded in your uploaded documents.

4. **Explore Blockchain Data:**

   - Use `/user_profile` to view your token balance, uploaded documents, and queries on-chain.

## Contributing

We welcome contributions that foster inquiry and critical thinking! To contribute:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m 'Add YourFeature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request with a clear description of your changes.

Please follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/0/code_of_conduct.html).

## License

The licensing terms for Socratic are to be determined. For now, all rights are reserved by the project maintainers. Please contact us for details on usage and distribution.

## Acknowledgments

- Inspired by the Socratic method, encouraging dialogue and exploration.
- Built with FastAPI, Solana, Anchor, and LangChain.
- Thanks to the open-source community for their invaluable tools and libraries.

## Questions?

Curious about Socratic? Here are some Socratic-style questions to guide your exploration:

- How might a decentralized platform transform the way we interact with knowledge?
- What are the implications of tokenizing document uploads for user incentives?
- How can we enhance Socratic to further foster collaborative learning?

Reach out via [GitHub Issues](https://github.com/yourusername/socratic/issues) or join our community discussion on X!
