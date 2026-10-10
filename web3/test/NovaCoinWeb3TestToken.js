import { expect } from "chai";
import hardhat from "hardhat";

const { ethers } = hardhat;

describe("NovaCoinWeb3TestToken", function () {
  const decimals = 10n ** 18n;
  const supply = 1_000n * decimals;
  const faucet = 100n * decimals;
  const claim = 10n * decimals;
  const addressLimit = 20n * decimals;

  async function deploy() {
    const [owner, user] = await ethers.getSigners();
    const factory = await ethers.getContractFactory("NovaCoinWeb3TestToken");
    const token = await factory.deploy(supply, faucet, claim, addressLimit);
    return { token, owner, user };
  }

  it("mints a fixed supply and supports ERC-20 transfers", async function () {
    const { token, owner, user } = await deploy();
    expect(await token.totalSupply()).to.equal(supply);
    await expect(token.transfer(user.address, claim))
      .to.emit(token, "Transfer")
      .withArgs(owner.address, user.address, claim);
    expect(await token.balanceOf(user.address)).to.equal(claim);
  });

  it("enforces bounded faucet distribution per address and globally", async function () {
    const { token, user } = await deploy();
    await expect(token.connect(user).claim()).to.emit(token, "Transfer");
    await expect(token.connect(user).claim()).to.emit(token, "Transfer");
    await expect(token.connect(user).claim()).to.be.revertedWith("Address limit reached");
  });

  it("rejects transfers above the available balance and invalid recipients", async function () {
    const { token, user } = await deploy();
    await expect(token.connect(user).transfer(user.address, 1)).to.be.revertedWith("Insufficient balance");
    await expect(token.transfer(ethers.ZeroAddress, 1)).to.be.revertedWith("Invalid recipient");
  });
});
