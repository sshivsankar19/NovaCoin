import { expect } from "chai";
import hardhat from "hardhat";

const { ethers } = hardhat;

describe("NovaCoinAnchor", function () {
  async function deploy() {
    const factory = await ethers.getContractFactory("NovaCoinAnchor");
    return factory.deploy();
  }

  it("stores and emits an anchor", async function () {
    const contract = await deploy();
    const hash = ethers.keccak256(ethers.toUtf8Bytes("NovaCoin block"));
    const transaction = await contract.anchorBlock(2, hash);
    await expect(transaction)
      .to.emit(contract, "BlockAnchored")
      .withArgs(2, hash, (await ethers.getSigners())[0].address);

    const anchor = await contract.getAnchor(2);
    expect(anchor[0]).to.equal(2);
    expect(anchor[1]).to.equal(hash);
    expect(anchor[3]).to.equal((await ethers.getSigners())[0].address);
  });

  it("rejects duplicate indexes and invalid values", async function () {
    const contract = await deploy();
    const hash = `0x${"11".repeat(32)}`;
    await expect(contract.anchorBlock(0, hash)).to.be.revertedWith("Invalid block index");
    await expect(contract.anchorBlock(1, ethers.ZeroHash)).to.be.revertedWith("Invalid block hash");
    await contract.anchorBlock(1, hash);
    await expect(contract.anchorBlock(1, hash)).to.be.revertedWith("Already anchored");
  });
});
