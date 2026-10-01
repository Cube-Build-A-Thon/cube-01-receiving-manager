const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function healthCheck() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  return response.json();
}

export async function createInspection(poData) {
  const response = await fetch(`${API_BASE_URL}/api/inspections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ po: poData }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Failed to create inspection');
  }

  return response.json();
}

export async function getInspection(inspectionId) {
  const response = await fetch(`${API_BASE_URL}/api/inspections/${inspectionId}`);
  if (!response.ok) {
    throw new Error('Inspection not found');
  }
  return response.json();
}

export async function uploadInspectionImages(inspectionId, files) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await fetch(`${API_BASE_URL}/api/inspections/${inspectionId}/images`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Failed to upload images');
  }

  return response.json();
}

export async function analyzeInspection(inspectionId, scenario = '') {
  const url = new URL(`${API_BASE_URL}/api/inspections/${inspectionId}/analyze`);
  if (scenario) url.searchParams.set('scenario', scenario);

  const response = await fetch(url, { method: 'POST' });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Analysis failed');
  }

  return response.json();
}

export async function overrideInspection(inspectionId, decision, reason) {
  const response = await fetch(`${API_BASE_URL}/api/inspections/${inspectionId}/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Override failed');
  }

  return response.json();
}

export function getInspectionImageUrl(inspectionId, imageId) {
  return `${API_BASE_URL}/api/inspections/${inspectionId}/images/${imageId}`;
}
