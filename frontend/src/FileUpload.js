import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import './FileUpload.css';

function FileUpload() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);

  const onDrop = (acceptedFiles) => {
    setFiles(acceptedFiles);
    setResults(null);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg']
    },
    multiple: true
  });

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('Please select files first!');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    
    files.forEach((file) => {
      formData.append('documents', file);
    });

    try {
      const response = await axios.post('http://insurance-system-65j.onrender.com/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResults(response.data);
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Make sure backend is running!');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <h1>Medical Insurance Claims Validator</h1>
      
      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        {isDragActive ? (
          <p>Drop files here...</p>
        ) : (
          <p>Drag & drop medical documents, or click to select</p>
        )}
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <h3>Selected Files:</h3>
          <ul>
            {files.map((file, index) => (
              <li key={index}>{file.name}</li>
            ))}
          </ul>
        </div>
      )}

      <button onClick={handleUpload} disabled={uploading}>
        {uploading ? 'Uploading...' : 'Upload & Validate'}
      </button>

      {results && (
        <div className="results">
          <h2>Results</h2>
          <p>Completion: {results.completion_percentage}%</p>
          <p>Status: {results.eligibility_status}</p>
        </div>
      )}
    </div>
  );
}

export default FileUpload;