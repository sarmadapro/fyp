import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Trash2, CheckCircle, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { portalUploadDocument, portalDeleteDocument, portalDocumentStatus } from '../api/client';

export default function UploadPage() {
  const [docStatus, setDocStatus] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const fetchDocStatus = async () => {
    try {
      const status = await portalDocumentStatus();
      setDocStatus(status);
    } catch (err) {
      console.error('Failed to fetch doc status:', err);
    }
  };

  useEffect(() => {
    fetchDocStatus();
  }, []);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!['.pdf', '.docx', '.txt'].includes(ext)) {
      toast.error('Unsupported file type. Please upload PDF, DOCX, or TXT.');
      return;
    }

    setUploading(true);
    setUploadProgress(10);

    try {
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 15, 85));
      }, 500);

      const result = await portalUploadDocument(file);

      clearInterval(progressInterval);
      setUploadProgress(100);

      toast.success(`${result.document_name} uploaded — ${result.chunk_count} chunks created`);
      await fetchDocStatus();
    } catch (err) {
      toast.error(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  }, []);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await portalDeleteDocument();
      toast.success('Document deleted');
      await fetchDocStatus();
    } catch (err) {
      toast.error(err.message || 'Delete failed');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <>
      <div className="page-header">
        <h2>Knowledge Base</h2>
        <p>
          Upload a document to power your AI assistant.
          {docStatus?.has_document && (
            <span style={{ color: 'var(--text-tertiary)', marginLeft: '0.5rem' }}>
              · Uploading a new file will replace the current one.
            </span>
          )}
        </p>
      </div>
      <div className="page-body">
        <div className="upload-container">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'active' : ''}`}
          >
            <input {...getInputProps()} />
            <div className="dropzone-icon">
              <Upload />
            </div>
            <h3>
              {isDragActive
                ? 'Drop your file here'
                : docStatus?.has_document
                  ? 'Drop a new file to replace current document'
                  : 'Drag & drop a document'}
            </h3>
            <p>
              or <span className="highlight">browse files</span>
            </p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              Supports PDF, DOCX, TXT · Max 50 MB · One document at a time
            </p>
          </div>

          {/* Upload Progress */}
          {uploading && (
            <div className="upload-progress">
              <div className="file-info">
                <FileText size={18} style={{ color: 'var(--accent-primary)' }} />
                <span className="file-name">Processing document...</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                Extracting text, creating embeddings, and building search index...
              </p>
            </div>
          )}

          {/* Current Document Card */}
          {docStatus?.has_document && !uploading && (
            <div className="current-doc-card">
              <h3>Active Document</h3>
              <div className="current-doc-info">
                <div className="current-doc-details">
                  <div className="doc-icon">
                    <FileText size={20} />
                  </div>
                  <div>
                    <div className="doc-name">{docStatus.document_name}</div>
                    <div className="doc-chunks">
                      {docStatus.chunk_count} chunks indexed · Ready to chat
                    </div>
                  </div>
                </div>
                <button className="btn btn-danger" onClick={handleDelete}>
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            </div>
          )}

          {/* No Document State */}
          {docStatus && !docStatus.has_document && !uploading && (
            <div style={{ textAlign: 'center', marginTop: '2rem', color: 'var(--text-tertiary)' }}>
              <AlertCircle size={24} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
              <p style={{ fontSize: '0.875rem' }}>
                No document uploaded yet. Upload one to get started!
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
