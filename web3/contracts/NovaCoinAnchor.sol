// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract NovaCoinAnchor {
    struct Anchor {
        uint256 novaBlockIndex;
        bytes32 blockHash;
        uint256 anchoredAt;
        address submitter;
    }

    mapping(uint256 => Anchor) public anchors;

    event BlockAnchored(
        uint256 indexed novaBlockIndex,
        bytes32 indexed blockHash,
        address indexed submitter
    );

    function anchorBlock(uint256 novaBlockIndex, bytes32 blockHash) external {
        require(novaBlockIndex > 0, "Invalid block index");
        require(blockHash != bytes32(0), "Invalid block hash");
        require(anchors[novaBlockIndex].blockHash == bytes32(0), "Already anchored");

        anchors[novaBlockIndex] = Anchor({
            novaBlockIndex: novaBlockIndex,
            blockHash: blockHash,
            anchoredAt: block.timestamp,
            submitter: msg.sender
        });

        emit BlockAnchored(novaBlockIndex, blockHash, msg.sender);
    }

    function getAnchor(uint256 novaBlockIndex)
        external
        view
        returns (uint256, bytes32, uint256, address)
    {
        Anchor memory anchor = anchors[novaBlockIndex];
        return (
            anchor.novaBlockIndex,
            anchor.blockHash,
            anchor.anchoredAt,
            anchor.submitter
        );
    }
}
