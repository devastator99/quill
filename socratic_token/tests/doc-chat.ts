import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { SocraticToken } from "../target/types/socratic_token";
import { assert } from "chai";
import { BN } from "bn.js";

describe("socratic_token", () => {
  // Configure provider and program
  anchor.setProvider(anchor.AnchorProvider.env());
  const provider = anchor.getProvider() as anchor.AnchorProvider;
  const program = anchor.workspace.SocraticToken as Program<SocraticToken>;
  const user = provider.wallet; // default test wallet

  // PDAs and bumps
  let userAccountPda: anchor.web3.PublicKey;
  let userAccountBump: number;
  let treasuryPda: anchor.web3.PublicKey;
  let treasuryBump: number;

  before(async () => {
    // Find PDAs for user account and treasury
    [userAccountPda, userAccountBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("user"), user.publicKey.toBuffer()],
      program.programId
    );
    [treasuryPda, treasuryBump] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("treasury")],
      program.programId
    );
    // We remove the code that creates the treasury account because it is a PDA and should be created by the program
  });

  it("initialize_user: should create a user account with defaults", async () => {
    await program.rpc.initializeUser({
      accounts: {
        userAccount: userAccountPda,
        user: user.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      },
    });

    const acct = await program.account.userAccount.fetch(userAccountPda);
    assert.ok(acct.owner.equals(user.publicKey));
    assert.equal(acct.tokenBalance.toNumber(), 0);
    assert.equal(acct.documentsUploaded.toNumber(), 0);
    assert.equal(acct.queriesMade.toNumber(), 0);
    assert.equal(acct.reputationScore.toNumber(), 0);
    assert.ok(acct.createdAt.toNumber() > 0);
  });

  it("purchase_tokens: should transfer SOL and mint tokens", async () => {
    const solAmount = new BN(1);
    await program.rpc.purchaseTokens(solAmount, {
      accounts: {
        userAccount: userAccountPda,
        user: user.publicKey,
        treasury: treasuryPda,
        systemProgram: anchor.web3.SystemProgram.programId,
      },
    });

    const acct = await program.account.userAccount.fetch(userAccountPda);
    // 1 SOL -> 1 * 1000 tokens
    assert.equal(acct.tokenBalance.toNumber(), 1000);
  });

  it("upload_document: success path deducts tokens and stores metadata", async () => {
    const docIndex = new BN(0);
    const [docPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("document"),
        user.publicKey.toBuffer(),
        docIndex.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    await program.rpc.uploadDocument(
      "QmPdfHashExample",
      1,               // access_level
      docIndex,        // document_index
      {
        accounts: {
          userAccount: userAccountPda,
          documentRecord: docPda,
          user: user.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        },
      }
    );

    // verify user account updated
    const acct = await program.account.userAccount.fetch(userAccountPda);
    assert.equal(acct.tokenBalance.toNumber(), 1000 - 10);
    assert.equal(acct.documentsUploaded.toNumber(), 1);

    // verify document record
    const doc = await program.account.documentRecord.fetch(docPda);
    assert.ok(doc.owner.equals(user.publicKey));
    assert.equal(doc.pdfHash, "QmPdfHashExample");
    assert.equal(doc.tokenCost.toNumber(), 10);
    assert.equal(doc.accessLevel, 1);
    assert.equal(doc.downloadCount.toNumber(), 0);
    assert.isTrue(doc.isActive);
    assert.ok(doc.uploadTimestamp.toNumber() > 0);
  });

  it("upload_document: invalid index should error", async () => {
    const badIndex = new BN(0); // but documentsUploaded is now 1
    const [badPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("document"),
        user.publicKey.toBuffer(),
        badIndex.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    try {
      await program.rpc.uploadDocument(
        "AnotherHash",
        1,
        badIndex,
        {
          accounts: {
            userAccount: userAccountPda,
            documentRecord: badPda,
            user: user.publicKey,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
        }
      );
      assert.fail("Expected InvalidDocumentIndex");
    } catch (err: any) {
      assert.include(err.toString(), "InvalidDocumentIndex");
    }
  });

  it("chat_query: success path deducts token and records query", async () => {
    const queryIndex = new BN(0);
    const [qryPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("query"),
        user.publicKey.toBuffer(),
        queryIndex.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    await program.rpc.chatQuery(
      "What is cortisol?",
      queryIndex,
      {
        accounts: {
          userAccount: userAccountPda,
          queryRecord: qryPda,
          user: user.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        },
      }
    );

    const acct = await program.account.userAccount.fetch(userAccountPda);
    assert.equal(acct.tokenBalance.toNumber(), 1000 - 10 - 1);
    assert.equal(acct.queriesMade.toNumber(), 1);

    const qry = await program.account.queryRecord.fetch(qryPda);
    assert.ok(qry.user.equals(user.publicKey));
    assert.equal(qry.queryText, "What is cortisol?");
    assert.equal(qry.tokensSpent.toNumber(), 1);
    assert.ok(qry.timestamp.toNumber() > 0);
  });

  it("chat_query: invalid index should error", async () => {
    const badIndex = new BN(0); // queriesMade == 1
    const [badPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("query"),
        user.publicKey.toBuffer(),
        badIndex.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    try {
      await program.rpc.chatQuery(
        "Invalid index test",
        badIndex,
        {
          accounts: {
            userAccount: userAccountPda,
            queryRecord: badPda,
            user: user.publicKey,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
        }
      );
      assert.fail("Expected InvalidQueryIndex");
    } catch (err: any) {
      assert.include(err.toString(), "InvalidQueryIndex");
    }
  });

  it("share_document: only owner can update and token is deducted", async () => {
    // share the first document (index 0)
    const docIndex = new BN(0);
    const [docPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("document"),
        user.publicKey.toBuffer(),
        docIndex.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    // change access_level to 2
    await program.rpc.shareDocument(
      2,
      {
        accounts: {
          userAccount: userAccountPda,
          documentRecord: docPda,
          user: user.publicKey,
        },
      }
    );

    const acct = await program.account.userAccount.fetch(userAccountPda);
    assert.equal(acct.tokenBalance.toNumber(), 1000 - 10 - 1 - 2);

    const doc = await program.account.documentRecord.fetch(docPda);
    assert.equal(doc.accessLevel, 2);
  });

  it("share_document: non-owner should error NotDocumentOwner", async () => {
    // create a poor user with zero tokens but wrong owner check fires first
    const poor = anchor.web3.Keypair.generate();
    // fund for fees
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(poor.publicKey, anchor.web3.LAMPORTS_PER_SOL),
      "confirmed"
    );
    const [poorUserPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("user"), poor.publicKey.toBuffer()],
      program.programId
    );
    // initialize poor user
    await program.rpc.initializeUser({
      accounts: {
        userAccount: poorUserPda,
        user: poor.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      },
      signers: [poor],
    });

    const docIndex = new BN(0);
    const [docPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("document"),
        user.publicKey.toBuffer(),
        docIndex.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    try {
      await program.rpc.shareDocument(
        5,
        {
          accounts: {
            userAccount: poorUserPda,
            documentRecord: docPda,
            user: poor.publicKey,
          },
          signers: [poor],
        }
      );
      assert.fail("Expected NotDocumentOwner");
    } catch (err: any) {
      assert.include(err.toString(), "NotDocumentOwner");
    }
  });

  it("generate_quiz: success path deducts tokens and stores quiz", async () => {
    const ts = Math.floor(Date.now() / 1000);
    const timestamp = new BN(ts);
    const [quizPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("quiz"),
        user.publicKey.toBuffer(),
        timestamp.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    await program.rpc.generateQuiz(
      "QmPdfHashExample",
      timestamp,
      {
        accounts: {
          userAccount: userAccountPda,
          quizRecord: quizPda,
          user: user.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        },
      }
    );

    const acct = await program.account.userAccount.fetch(userAccountPda);
    assert.equal(acct.tokenBalance.toNumber(), 1000 - 10 - 1 - 2 - 5);

    const quiz = await program.account.quizRecord.fetch(quizPda);
    assert.ok(quiz.creator.equals(user.publicKey));
    assert.equal(quiz.documentHash, "QmPdfHashExample");
    assert.equal(quiz.tokensSpent.toNumber(), 5);
    assert.isFalse(quiz.isPublic);
    assert.equal(quiz.createdAt.toNumber(), ts);
  });

  it("generate_quiz: insufficient tokens should error", async () => {
    // use poor user with 0 tokens
    const poor = anchor.web3.Keypair.generate();
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(poor.publicKey, anchor.web3.LAMPORTS_PER_SOL),
      "confirmed"
    );
    const [poorUserPda] = await anchor.web3.PublicKey.findProgramAddress(
      [Buffer.from("user"), poor.publicKey.toBuffer()],
      program.programId
    );
    await program.rpc.initializeUser({
      accounts: {
        userAccount: poorUserPda,
        user: poor.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      },
      signers: [poor],
    });

    const ts = Math.floor(Date.now() / 1000);
    const timestamp = new BN(ts);
    const [quizPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("quiz"),
        poor.publicKey.toBuffer(),
        timestamp.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    try {
      await program.rpc.generateQuiz(
        "AnyHash",
        timestamp,
        {
          accounts: {
            userAccount: poorUserPda,
            quizRecord: quizPda,
            user: poor.publicKey,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
          signers: [poor],
        }
      );
      assert.fail("Expected InsufficientTokens");
    } catch (err: any) {
      assert.include(err.toString(), "InsufficientTokens");
    }
  });

  it("stake_tokens: enforcing minimum and balance checks", async () => {
    // insufficient stake amount (<100)
    const ts = Math.floor(Date.now() / 1000);
    const timestamp = new BN(ts);

    const [stakePda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("stake"),
        user.publicKey.toBuffer(),
        timestamp.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    try {
      await program.rpc.stakeTokens(
        new BN(50),
        timestamp,
        {
          accounts: {
            userAccount: userAccountPda,
            stakeRecord: stakePda,
            user: user.publicKey,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
        }
      );
      assert.fail("Expected InsufficientStakeAmount");
    } catch (err: any) {
      assert.include(err.toString(), "InsufficientStakeAmount");
    }

    // insufficient tokens for a large stake
    try {
      await program.rpc.stakeTokens(
        new BN(1_000_000),
        timestamp,
        {
          accounts: {
            userAccount: userAccountPda,
            stakeRecord: stakePda,
            user: user.publicKey,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
        }
      );
      assert.fail("Expected InsufficientTokens");
    } catch (err: any) {
      assert.include(err.toString(), "InsufficientTokens");
    }
  });

  let stakeNowPda: anchor.web3.PublicKey;
  let stakeNowTs: number;

  it("stake_tokens: successful staking", async () => {
    stakeNowTs = Math.floor(Date.now() / 1000);
    const timestamp = new BN(stakeNowTs);
    [stakeNowPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("stake"),
        user.publicKey.toBuffer(),
        timestamp.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    await program.rpc.stakeTokens(
      new BN(100),
      timestamp,
      {
        accounts: {
          userAccount: userAccountPda,
          stakeRecord: stakeNowPda,
          user: user.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        },
      }
    );

    const acct = await program.account.userAccount.fetch(userAccountPda);
    assert.equal(acct.tokenBalance.toNumber(), 1000 - 10 - 1 - 2 - 5 - 100);

    const stake = await program.account.stakeRecord.fetch(stakeNowPda);
    assert.ok(stake.user.equals(user.publicKey));
    assert.equal(stake.amount.toNumber(), 100);
    assert.equal(stake.stakedAt.toNumber(), stakeNowTs);
    assert.isTrue(stake.isActive);
  });

  it("unstake_tokens: too early should error StakeCooldownActive", async () => {
    try {
      await program.rpc.unstakeTokens({
        accounts: {
          userAccount: userAccountPda,
          stakeRecord: stakeNowPda,
          user: user.publicKey,
        },
      });
      assert.fail("Expected StakeCooldownActive");
    } catch (err: any) {
      assert.include(err.toString(), "StakeCooldownActive");
    }
  });

  it("stake & unstake after cooldown: full cycle success", async () => {
    // stake again with timestamp far in the past
    const pastTs = Math.floor(Date.now() / 1000) - 604800 - 10; // 7 days + buffer
    const pastBn = new BN(pastTs);
    const [pastPda] = await anchor.web3.PublicKey.findProgramAddress(
      [
        Buffer.from("stake"),
        user.publicKey.toBuffer(),
        pastBn.toArrayLike(Buffer, "le", 8),
      ],
      program.programId
    );

    // stake
    await program.rpc.stakeTokens(
      new BN(100),
      pastBn,
      {
        accounts: {
          userAccount: userAccountPda,
          stakeRecord: pastPda,
          user: user.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        },
      }
    );

    // balance before unstake
    const before = (await program.account.userAccount.fetch(userAccountPda)).tokenBalance.toNumber();

    // unstake should now succeed
    await program.rpc.unstakeTokens({
      accounts: {
        userAccount: userAccountPda,
        stakeRecord: pastPda,
        user: user.publicKey,
      },
    });

    const after = (await program.account.userAccount.fetch(userAccountPda)).tokenBalance.toNumber();
    assert.equal(after, before + 100, "Tokens should be returned on unstake");

    const stake = await program.account.stakeRecord.fetch(pastPda);
    assert.isFalse(stake.isActive, "Stake record should be marked inactive");
  });
});
