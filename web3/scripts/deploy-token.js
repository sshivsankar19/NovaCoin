import hre from "hardhat";

if (hre.network.name !== "hederaTestnet") {
  throw new Error("Deployment is restricted to the Hedera Testnet network.");
}
if (!process.env.HEDERA_PRIVATE_KEY) {
  throw new Error("Set HEDERA_PRIVATE_KEY in a local, ignored .env file.");
}

const ethers = hre.ethers;
const decimals = 10n ** 18n;
const totalSupply = 1_000_000n * decimals;
const faucetAllocation = 100_000n * decimals;
const claimAmount = 100n * decimals;
const perAddressLimit = 500n * decimals;
const factory = await ethers.getContractFactory("NovaCoinWeb3TestToken");
const contract = await factory.deploy(
  totalSupply,
  faucetAllocation,
  claimAmount,
  perAddressLimit,
);
const deploymentTransaction = contract.deploymentTransaction();
await contract.waitForDeployment();

const address = await contract.getAddress();
const txHash = deploymentTransaction?.hash || "Unavailable";
console.log(`Hedera network: testnet (chain ID 296)`);
console.log(`Token address: ${address}`);
console.log(`Deployment transaction: ${txHash}`);
if (txHash !== "Unavailable") {
  console.log(`HashScan: https://hashscan.io/testnet/transaction/${txHash}`);
}
