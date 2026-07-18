// Chart.js global configurations for dark theme
Chart.defaults.color = '#94A3B8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';
Chart.defaults.font.family = "'Outfit', sans-serif";

document.addEventListener('DOMContentLoaded', () => {
    // 1. ML Model Comparison Chart
    const mlCtx = document.getElementById('mlComparisonChart').getContext('2d');
    new Chart(mlCtx, {
        type: 'bar',
        data: {
            labels: ['Decision Tree', 'Random Forest', 'Logistic Regression', 'XGBoost (Auto-Triage)'],
            datasets: [{
                label: 'Validation Accuracy (%)',
                data: [77.0, 85.0, 88.0, 96.0],
                backgroundColor: [
                    'rgba(255, 118, 117, 0.6)',
                    'rgba(255, 118, 117, 0.8)',
                    'rgba(108, 92, 231, 0.6)',
                    'rgba(108, 92, 231, 1.0)'
                ],
                borderColor: [
                    '#FF7675',
                    '#FF7675',
                    '#6C5CE7',
                    '#6C5CE7'
                ],
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    // 2. Scorecard Weights (Model 3 Drivers)
    const driversCtx = document.getElementById('driversChart').getContext('2d');
    new Chart(driversCtx, {
        type: 'bar',
        data: {
            labels: ['Age (Scaled)', 'BMI (Scaled)', 'Claim Freq', 'Claim Severity', 'Smoking Status'],
            datasets: [{
                label: 'OLS Regression Coefficient',
                data: [4.49, 6.04, 6.42, 10.66, 14.99],
                backgroundColor: 'rgba(255, 118, 117, 0.8)',
                borderColor: '#FF7675',
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    // 3. Claim Frequency Drivers OLS Chart (Model 1)
    const scorecardCtx = document.getElementById('scorecardChart').getContext('2d');
    new Chart(scorecardCtx, {
        type: 'bar',
        data: {
            labels: ['Age (Scaled)', 'Smoker Status', 'Gender', 'BMI (Scaled)', 'Income', 'Dependents'],
            datasets: [{
                label: 'OLS Regression Coefficient',
                data: [0.2101, -0.0115, -0.0107, 0.0039, 0.0002, 0.0012],
                backgroundColor: [
                    'rgba(108, 92, 231, 0.9)', // Age: highly significant
                    'rgba(255, 255, 255, 0.1)', // Smoker: not significant
                    'rgba(255, 255, 255, 0.1)', // Gender: not significant
                    'rgba(255, 255, 255, 0.1)', // BMI: not significant
                    'rgba(255, 255, 255, 0.1)', // Income: not significant
                    'rgba(255, 255, 255, 0.1)'  // Dependents: not significant
                ],
                borderColor: [
                    '#6C5CE7',
                    'rgba(255, 255, 255, 0.2)',
                    'rgba(255, 255, 255, 0.2)',
                    'rgba(255, 255, 255, 0.2)',
                    'rgba(255, 255, 255, 0.2)',
                    'rgba(255, 255, 255, 0.2)'
                ],
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            if (context.dataIndex === 0) {
                                return 'Statistically highly significant (p < 0.001)';
                            } else {
                                return 'Not statistically significant (p > 0.05)';
                            }
                        }
                    }
                }
            }
        }
    });
});
