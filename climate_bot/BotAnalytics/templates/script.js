// Simulated data update (In practice, this would be fetched from your API)
const data = {
    totalUsers: 1500,
    activeUsers: 1200,
    newUsers: 300,
    inactiveUsers: 300,
    engagementRate: 80,
    totalCommands: 5000,
    commandUsage: { '/start': 2500, '/help': 1500 },
    botUptime: 98,
    responseTime: 1.2, // in seconds
};

// Update the DOM with the data
document.getElementById('total-users').textContent = data.totalUsers;
document.getElementById('active-users').textContent = data.activeUsers;
document.getElementById('new-users').textContent = data.newUsers;
document.getElementById('inactive-users').textContent = data.inactiveUsers;
document.getElementById('engagement-rate').textContent = `${data.engagementRate}%`;
document.getElementById('total-commands').textContent = data.totalCommands;
document.getElementById('command-usage').textContent = `/start: ${data.commandUsage['/start']}, /help: ${data.commandUsage['/help']}`;
document.getElementById('bot-uptime').textContent = `${data.botUptime}%`;
document.getElementById('response-time').textContent = `${data.responseTime}s`;

// Chart.js data and configuration
const activeUsersData = {
    labels: ['Active Users', 'Inactive Users'],
    datasets: [{
        data: [data.activeUsers, data.inactiveUsers],
        backgroundColor: ['#0078D4', '#ddd'],
        hoverBackgroundColor: ['#0057A5', '#bbb']
    }]
};

const commandUsageData = {
    labels: Object.keys(data.commandUsage),
    datasets: [{
        label: 'Command Usage',
        data: Object.values(data.commandUsage),
        backgroundColor: '#0078D4',
        borderColor: '#0057A5',
        borderWidth: 1
    }]
};

const botUptimeData = {
    labels: ['Uptime', 'Downtime'],
    datasets: [{
        data: [data.botUptime, 100 - data.botUptime],
        backgroundColor: ['#0078D4', '#ddd'],
        hoverBackgroundColor: ['#0057A5', '#bbb']
    }]
};

// Create charts using Chart.js
new Chart(document.getElementById('activeUsersChart'), {
    type: 'pie',
    data: activeUsersData
});

new Chart(document.getElementById('commandUsageChart'), {
    type: 'bar',
    data: commandUsageData,
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

new Chart(document.getElementById('botUptimeChart'), {
    type: 'pie',
    data: botUptimeData
});
