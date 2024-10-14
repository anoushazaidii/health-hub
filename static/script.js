document.getElementById('healthForm').addEventListener('submit', logHealthData);

function logHealthData(e) {
  e.preventDefault();
  
  let bloodSugar = document.getElementById('bloodSugar').value;
  let bloodPressure = document.getElementById('bloodPressure').value;
  let medication = document.getElementById('medication').value;
  
  let healthData = {
    bloodSugar: bloodSugar,
    bloodPressure: bloodPressure,
    medication: medication,
    date: new Date().toLocaleDateString()
  };

  // Store data in localStorage (simplified for prototype)
  let healthLogs = JSON.parse(localStorage.getItem('healthLogs')) || [];
  healthLogs.push(healthData);
  localStorage.setItem('healthLogs', JSON.stringify(healthLogs));
  
  // Display insights
  displayInsights();
}

function displayInsights() {
  let healthLogs = JSON.parse(localStorage.getItem('healthLogs')) || [];
  
  if (healthLogs.length > 0) {
    let avgBloodSugar = healthLogs.reduce((sum, log) => sum + parseInt(log.bloodSugar), 0) / healthLogs.length;
    document.getElementById('insights').innerText = `Average Blood Sugar: ${avgBloodSugar.toFixed(2)} mg/dL`;
  }
}

function addReminder() {
  let reminderText = prompt('Enter reminder (e.g., Medication at 8 PM)');
  
  if (reminderText) {
    let reminderList = document.getElementById('reminderList');
    let li = document.createElement('li');
    li.innerText = reminderText;
    reminderList.appendChild(li);
  }
}
