use anchor_lang::prelude::*;

declare_id!("5AhcUJj8WtAqR6yfff76HyZFX7LWovRZ1bcgN9n3Rwa7");

#[program]
pub mod socratic_token {
    use super::*;

    pub fn initialize_user(ctx: Context<InitializeUser>) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        user_account.owner = ctx.accounts.user.key();
        user_account.token_balance = 0;
        user_account.documents_uploaded = 0;
        user_account.queries_made = 0;
        user_account.reputation_score = 0;
        user_account.created_at = Clock::get()?.unix_timestamp;
        
        msg!("User account initialized for: {}", ctx.accounts.user.key());
        Ok(())
    }

    pub fn upload_document(
        ctx: Context<UploadDocument>,
        pdf_hash: String,
        access_level: u8,
        document_index: u64,
    ) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        
        // Validate document_index
        require!(
            document_index == user_account.documents_uploaded,
            SocraticError::InvalidDocumentIndex
        );
        
        // Check if user has enough tokens
        require!(
            user_account.token_balance >= UPLOAD_DOCUMENT_COST,
            SocraticError::InsufficientTokens
        );

        // Deduct tokens
        user_account.token_balance -= UPLOAD_DOCUMENT_COST;
        user_account.documents_uploaded += 1;

        // Create document record
        let document_record = &mut ctx.accounts.document_record;
        document_record.owner = ctx.accounts.user.key();
        document_record.pdf_hash = pdf_hash;
        document_record.upload_timestamp = Clock::get()?.unix_timestamp;
        document_record.token_cost = UPLOAD_DOCUMENT_COST;
        document_record.access_level = access_level;
        document_record.download_count = 0;
        document_record.is_active = true;

        msg!("Document uploaded. Hash: {}, Cost: {} tokens", 
             document_record.pdf_hash, UPLOAD_DOCUMENT_COST);
        
        Ok(())
    }

    pub fn chat_query(
        ctx: Context<ChatQuery>,
        query_text: String,
        query_index: u64,
    ) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        
        // Validate query_index
        require!(
            query_index == user_account.queries_made,
            SocraticError::InvalidQueryIndex
        );
        
        // Check token balance
        require!(
            user_account.token_balance >= CHAT_QUERY_COST,
            SocraticError::InsufficientTokens
        );

        // Deduct tokens
        user_account.token_balance -= CHAT_QUERY_COST;
        user_account.queries_made += 1;

        // Create query record
        let query_record = &mut ctx.accounts.query_record;
        query_record.user = ctx.accounts.user.key();
        query_record.query_text = query_text;
        query_record.timestamp = Clock::get()?.unix_timestamp;
        query_record.tokens_spent = CHAT_QUERY_COST;

        msg!("Query processed. Tokens spent: {}", CHAT_QUERY_COST);
        Ok(())
    }

    pub fn purchase_tokens(ctx: Context<PurchaseTokens>, sol_amount: u64) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        
        // Calculate tokens to mint (1 SOL = 1000 tokens)
        let tokens_to_mint = sol_amount.checked_mul(TOKEN_EXCHANGE_RATE)
            .ok_or(SocraticError::ArithmeticOverflow)?;
        
        // Transfer SOL to program treasury
        let cpi_context = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.user.to_account_info(),
                to: ctx.accounts.treasury.to_account_info(),
            },
        );
        anchor_lang::system_program::transfer(cpi_context, sol_amount)?;

        // Add tokens to user balance
        user_account.token_balance += tokens_to_mint;
        
        msg!("Purchased {} tokens for {} SOL", tokens_to_mint, sol_amount);
        Ok(())
    }

    pub fn share_document(ctx: Context<ShareDocument>, new_access_level: u8) -> Result<()> {
        let document_record = &mut ctx.accounts.document_record;
        let user_account = &mut ctx.accounts.user_account;
        
        // Only owner can modify access level
        require!(
            document_record.owner == ctx.accounts.user.key(),
            SocraticError::NotDocumentOwner
        );

        // Charge tokens for sharing
        require!(
            user_account.token_balance >= SHARE_DOCUMENT_COST,
            SocraticError::InsufficientTokens
        );

        user_account.token_balance -= SHARE_DOCUMENT_COST;
        document_record.access_level = new_access_level;
        
        msg!("Document access level updated to: {}", new_access_level);
        Ok(())
    }

    pub fn generate_quiz(
        ctx: Context<GenerateQuiz>,
        document_hash: String,
        timestamp: u64,
    ) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        
        // Check token balance
        require!(
            user_account.token_balance >= QUIZ_GENERATION_COST,
            SocraticError::InsufficientTokens
        );

        // Deduct tokens
        user_account.token_balance -= QUIZ_GENERATION_COST;
        
        // Create quiz record
        let quiz_record = &mut ctx.accounts.quiz_record;
        quiz_record.creator = ctx.accounts.user.key();
        quiz_record.document_hash = document_hash;
        quiz_record.created_at = timestamp as i64;
        quiz_record.tokens_spent = QUIZ_GENERATION_COST;
        quiz_record.is_public = false;

        msg!("Quiz generation initiated for document: {}", quiz_record.document_hash);
        Ok(())
    }

    pub fn stake_tokens(
        ctx: Context<StakeTokens>,
        amount: u64,
        timestamp: u64,
    ) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        
        // Check if user has enough tokens
        require!(
            user_account.token_balance >= amount,
            SocraticError::InsufficientTokens
        );

        require!(
            amount >= MINIMUM_STAKE_AMOUNT,
            SocraticError::InsufficientStakeAmount
        );

        // Create staking record
        let stake_record = &mut ctx.accounts.stake_record;
        stake_record.user = ctx.accounts.user.key();
        stake_record.amount = amount;
        stake_record.staked_at = timestamp as i64;
        stake_record.is_active = true;

        // Deduct from balance
        user_account.token_balance -= amount;
        
        msg!("Staked {} tokens for premium features", amount);
        Ok(())
    }

    pub fn unstake_tokens(ctx: Context<UnstakeTokens>) -> Result<()> {
        let stake_record = &mut ctx.accounts.stake_record;
        let user_account = &mut ctx.accounts.user_account;
        let current_time = Clock::get()?.unix_timestamp;
        
        // Check if user is the owner of the stake record
        require!(
            stake_record.user == ctx.accounts.user.key(),
            SocraticError::NotStakeOwner
        );
        
        // Check cooldown period
        require!(
            current_time >= stake_record.staked_at + STAKE_COOLDOWN_PERIOD,
            SocraticError::StakeCooldownActive
        );

        // Return tokens to user
        user_account.token_balance += stake_record.amount;
        stake_record.is_active = false;
        
        msg!("Unstaked {} tokens", stake_record.amount);
        Ok(())
    }
}

// Constants
const UPLOAD_DOCUMENT_COST: u64 = 10;
const CHAT_QUERY_COST: u64 = 1;
const QUIZ_GENERATION_COST: u64 = 5;
const SHARE_DOCUMENT_COST: u64 = 2;
const MINIMUM_STAKE_AMOUNT: u64 = 100;
const TOKEN_EXCHANGE_RATE: u64 = 1000;
const STAKE_COOLDOWN_PERIOD: i64 = 7 * 24 * 60 * 60;

// Account structures
#[account]
pub struct UserAccount {
    pub owner: Pubkey,
    pub token_balance: u64,
    pub documents_uploaded: u64,
    pub queries_made: u64,
    pub reputation_score: u64,
    pub created_at: i64,
}

#[account]
pub struct DocumentRecord {
    pub owner: Pubkey,
    pub pdf_hash: String,
    pub upload_timestamp: i64,
    pub token_cost: u64,
    pub access_level: u8,
    pub download_count: u64,
    pub is_active: bool,
}

#[account]
pub struct QueryRecord {
    pub user: Pubkey,
    pub query_text: String,
    pub timestamp: i64,
    pub tokens_spent: u64,
}

#[account]
pub struct QuizRecord {
    pub creator: Pubkey,
    pub document_hash: String,
    pub created_at: i64,
    pub tokens_spent: u64,
    pub is_public: bool,
}

#[account]
pub struct StakeRecord {
    pub user: Pubkey,
    pub amount: u64,
    pub staked_at: i64,
    pub is_active: bool,
}

// Context structures
#[derive(Accounts)]
pub struct InitializeUser<'info> {
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 8 + 8 + 8 + 8 + 8,
        seeds = [b"user", user.key().as_ref()],
        bump
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(pdf_hash: String, access_level: u8, document_index: u64)]
pub struct UploadDocument<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump,
        // Bail out *before* ever trying to create `document_record`:
        constraint = document_index == user_account.documents_uploaded @ SocraticError::InvalidDocumentIndex,
        // And also check the token-balance early:
        constraint = user_account.token_balance >= UPLOAD_DOCUMENT_COST @ SocraticError::InsufficientTokens,
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 4 + 256 + 8 + 8 + 1 + 8 + 1,
        seeds = [b"document", user.key().as_ref(), document_index.to_le_bytes().as_ref()],
        bump
    )]
    pub document_record: Account<'info, DocumentRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(query_text: String, query_index: u64)]
pub struct ChatQuery<'info> {
    #[account(
      mut,
      seeds = [b"user", user.key().as_ref()],
      bump,
      constraint = query_index == user_account.queries_made @ SocraticError::InvalidQueryIndex,
      constraint = user_account.token_balance >= CHAT_QUERY_COST @ SocraticError::InsufficientTokens,
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 4 + 512 + 8 + 8,
        seeds = [b"query", user.key().as_ref(), query_index.to_le_bytes().as_ref()],
        bump
    )]
    pub query_record: Account<'info, QueryRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct PurchaseTokens<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(mut)]
    pub user: Signer<'info>,
    /// CHECK: Treasury account is safe as it’s a PDA derived with seeds [b"treasury"] and controlled by the program
    // #[account(mut, seeds = [b"treasury"], bump)]
    
     /// PDA to collect SOL payments.  If it doesn’t exist yet, create it (space = 0).
    #[account(
      init_if_needed,
      payer = user,
      seeds = [b"treasury"],
      bump,
      space = 0
    )]
    pub treasury: AccountInfo<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ShareDocument<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(
        mut,
        // enforce “only the true owner may call” before anything else
        constraint = document_record.owner == user.key() @ SocraticError::NotDocumentOwner,
    )]
    pub document_record: Account<'info, DocumentRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(document_hash: String, timestamp: u64)]
pub struct GenerateQuiz<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump,
        // catch “no tokens to pay for quiz” *before* creating the PDA
        constraint = user_account.token_balance >= QUIZ_GENERATION_COST @ SocraticError::InsufficientTokens,
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 4 + 256 + 8 + 8 + 1,
        seeds = [b"quiz", user.key().as_ref(), timestamp.to_le_bytes().as_ref()],
        bump
    )]
    pub quiz_record: Account<'info, QuizRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(amount: u64, timestamp: u64)]
pub struct StakeTokens<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump,
        // 1) check “minimum stake” first
        constraint = amount >= MINIMUM_STAKE_AMOUNT @ SocraticError::InsufficientStakeAmount,
        // 2) then “enough balance”
        constraint = user_account.token_balance >= amount @ SocraticError::InsufficientTokens,
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 8 + 8 + 1,
        seeds = [b"stake", user.key().as_ref(), timestamp.to_le_bytes().as_ref()],
        bump
    )]
    pub stake_record: Account<'info, StakeRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UnstakeTokens<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(mut)]
    pub stake_record: Account<'info, StakeRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
}

// Error codes
#[error_code]
pub enum SocraticError {
    #[msg("Insufficient tokens to perform this action")]
    InsufficientTokens,
    #[msg("You are not the owner of this document")]
    NotDocumentOwner,
    #[msg("Insufficient amount to stake")]
    InsufficientStakeAmount,
    #[msg("Stake cooldown period is still active")]
    StakeCooldownActive,
    #[msg("Invalid document index")]
    InvalidDocumentIndex,
    #[msg("Invalid query index")]
    InvalidQueryIndex,
    #[msg("You are not the owner of this stake record")]
    NotStakeOwner,
    #[msg("Arithmetic overflow occurred")]
    ArithmeticOverflow,
}