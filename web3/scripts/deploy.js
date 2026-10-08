import hre from "hardhat";

const network = hre.network.name;
if (network !== "hederaTestnet") {
  throw new Error("Deployment is restricted to the Hedera Testnet network.");
}
if (!process.env.HEDERA_PRIVATE_KEY) {
  throw new Error("Set HEDERA_PRIVATE_KEY in a local, ignored .env file.");
}

const factory = await hre.ethers.getContractFactory("NovaCoinAnchor");
const contract = await factory.deploy();
const deploymentTransaction = contract.deploymentTransaction();
await contract.waitForDeployment();

const address = await contract.getAddress();
const txHash = deploymentTransaction?.hash || "Unavailable";
console.log(`Hedera network: testnet (chain ID 296)`);
console.log(`Contract address: ${address}`);
console.log(`Deployment transaction: ${txHash}`);
if (txHash !== "Unavailable") {
  console.log(`HashScan: https://hashscan.io/testnet/transaction/${txHash}`);
}
