// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract AlertRegistry {
    struct Alert {
        uint256 timestamp;
        string alertType;
        string details;
        uint8 severity;
    }

    Alert[] public alerts;
    address public owner;

    event AlertLogged(uint256 indexed id, string alertType, uint8 severity, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function logAlert(string calldata alertType, string calldata details, uint8 severity) external onlyOwner {
        uint256 id = alerts.length;
        alerts.push(Alert(block.timestamp, alertType, details, severity));
        emit AlertLogged(id, alertType, severity, block.timestamp);
    }

    function alertCount() external view returns (uint256) {
        return alerts.length;
    }

    function getAlert(uint256 id) external view returns (uint256 timestamp, string memory alertType, string memory details, uint8 severity) {
        Alert storage a = alerts[id];
        return (a.timestamp, a.alertType, a.details, a.severity);
    }
}
