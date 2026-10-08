import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config";

const privateKey = process.env.HEDERA_PRIVATE_KEY;

export default {
  solidity: "0.8.20",
  networks: {
    hardhat: {},
    hederaTestnet: {
      url: process.env.HEDERA_RPC_URL || "https://testnet.hashio.io/api",
      chainId: 296,
      accounts: privateKey ? [privateKey] : [],
    },
  },
};
