// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract NovaCoinWeb3TestToken {
    string public constant name = "NovaCoin Web3 Test Token";
    string public constant symbol = "tNVC";
    uint8 public constant decimals = 18;

    uint256 public immutable totalSupply;
    uint256 public immutable faucetAllocation;
    uint256 public immutable claimAmount;
    uint256 public immutable maxClaimPerAddress;
    uint256 public claimedFromFaucet;
    address public immutable owner;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => uint256) public claimedBy;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(
        uint256 initialSupply,
        uint256 faucetAmount,
        uint256 perClaim,
        uint256 perAddressLimit
    ) {
        require(initialSupply > 0, "Invalid supply");
        require(faucetAmount > 0 && faucetAmount <= initialSupply, "Invalid faucet");
        require(perClaim > 0 && perClaim <= perAddressLimit, "Invalid claim");
        owner = msg.sender;
        totalSupply = initialSupply;
        faucetAllocation = faucetAmount;
        claimAmount = perClaim;
        maxClaimPerAddress = perAddressLimit;
        balanceOf[msg.sender] = initialSupply;
        emit Transfer(address(0), msg.sender, initialSupply);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 permitted = allowance[from][msg.sender];
        require(permitted >= amount, "Allowance exceeded");
        allowance[from][msg.sender] = permitted - amount;
        _transfer(from, to, amount);
        return true;
    }

    function claim() external returns (bool) {
        require(claimedFromFaucet + claimAmount <= faucetAllocation, "Faucet exhausted");
        require(claimedBy[msg.sender] + claimAmount <= maxClaimPerAddress, "Address limit reached");
        claimedFromFaucet += claimAmount;
        claimedBy[msg.sender] += claimAmount;
        _transfer(owner, msg.sender, claimAmount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), "Invalid recipient");
        require(balanceOf[from] >= amount, "Insufficient balance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}
