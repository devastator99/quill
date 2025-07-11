use anchor_lang::prelude::*;

// Replace with your real program ID before deploying!
declare_id!("5AhcUJj8WtAqR6yfff76HyZFX7LWovRZ1bcgN9n3Rwa7");

#[program]
pub mod doc_chat {
    use super::*;

    // Maximum allowed length for the PDF hash
    pub const MAX_HASH_LENGTH: usize = 64;

    /// Stores or updates a user's PDF hash on-chain.
    /// 
    /// If the account doesn't exist, it's created; otherwise it's simply overwritten.
    pub fn store_hash(ctx: Context<StoreHash>, pdf_hash: String) -> Result<()> {
        // 1) Validate length
        require!(
            pdf_hash.len() <= MAX_HASH_LENGTH,
            ErrorCode::InvalidHashLength
        );

        // 2) Populate account
        let acct = &mut ctx.accounts.user_account;
        acct.owner    = *ctx.accounts.wallet.key;
        acct.pdf_hash = pdf_hash.clone();
        acct.timestamp = Clock::get()?.unix_timestamp;

        // 3) Emit logs for on-chain and off-chain consumption
        msg!("📥 Stored PDF hash for {} at {}", acct.owner, acct.timestamp);
        emit!(HashStored {
            owner: acct.owner,
            pdf_hash,
            timestamp: acct.timestamp,
        });

        Ok(())
    }

    /// An event that fires every time `store_hash` succeeds.
    #[event]
    pub struct HashStored {
        pub owner: Pubkey,
        pub pdf_hash: String,
        pub timestamp: i64,
    }
}

#[derive(Accounts)]
#[instruction(pdf_hash: String)]
pub struct StoreHash<'info> {
    /// Upsertable PDA: seeds = [ b"user", wallet.key().as_ref() ]
    /// We allocate enough space for:
    /// - 8 bytes Anchor discriminator  
    /// - 32 bytes Pubkey  
    /// - 8 bytes i64 timestamp  
    /// - 4 bytes string prefix + MAX_HASH_LENGTH bytes of UTF-8
    #[account(
        init_if_needed,
        payer = wallet,
        space = 8 + 32 + 8 + 4 + doc_chat::MAX_HASH_LENGTH,
        seeds = [ b"user", wallet.key().as_ref() ],
        bump
    )]
    pub user_account: Account<'info, UserAccount>,

    /// The signer who owns this account
    #[account(mut)]
    pub wallet: Signer<'info>,

    /// System program
    pub system_program: Program<'info, System>,
}

#[account]
pub struct UserAccount {
    /// Who wrote the hash
    pub owner:    Pubkey,
    /// The PDF hash (up to 64 bytes)
    pub pdf_hash: String,
    /// UNIX timestamp of last write
    pub timestamp: i64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("PDF hash must be 64 characters or less")]
    InvalidHashLength,
}
