import { useState, useEffect, useCallback, useRef, type DragEvent } from 'react';
import { FileText, Upload, X, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { TopBar } from '../components/TopBar';
import { getDocuments, uploadDocument, type Document } from '../lib/api';
import { toast } from '../components/Toast';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

export function KnowledgeBasePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadFileName, setUploadFileName] = useState('');
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch {
      toast('Failed to load documents', 'error');
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  async function handleFile(file: File) {
    setUploadFileName(file.name);
    setUploadStatus('uploading');
    setUploadError('');

    try {
      await uploadDocument(file);
      setUploadStatus('success');
      toast(`${file.name} indexed successfully`, 'success');
      fetchDocs();
    } catch (err) {
      setUploadStatus('error');
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setUploadError(msg);
      toast(msg, 'error');
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = '';
  }

  function closeModal() {
    setShowModal(false);
    setUploadStatus('idle');
    setUploadFileName('');
    setUploadError('');
  }

  return (
    <>
      <TopBar title="Knowledge Base" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-on-surface">
                Knowledge Base
              </h2>
              <p className="text-sm text-on-surface-muted mt-1">
                {documents.length} document{documents.length !== 1 ? 's' : ''} indexed
              </p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 bg-primary-container text-white px-4 py-2.5 rounded-lg text-sm font-semibold hover:opacity-90 active:scale-[0.98] transition-all shadow-lg shadow-primary-container/20"
            >
              <Upload size={16} />
              Upload document
            </button>
          </div>

          {/* Stats bar */}
          {documents.length > 0 && (
            <div className="flex gap-3 mb-8">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-surface rounded-full border border-outline/10 text-xs font-label text-on-surface-dim">
                <FileText size={12} />
                {documents.length} Documents
              </span>
            </div>
          )}

          {/* Document grid */}
          {documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-surface-high flex items-center justify-center">
                <FileText size={28} className="text-on-surface-muted" />
              </div>
              <h3 className="text-lg font-semibold text-on-surface">No documents yet</h3>
              <p className="text-sm text-on-surface-muted max-w-sm">
                Upload your first document to start building your knowledge base.
              </p>
              <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-2 bg-primary-container text-white px-4 py-2.5 rounded-lg text-sm font-semibold hover:opacity-90 transition-all"
              >
                <Upload size={16} />
                Upload your first document
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map((doc) => (
                <div
                  key={doc.doc_id}
                  className="bg-surface border border-outline/10 rounded-xl p-5 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-200 cursor-default"
                >
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-surface-high flex items-center justify-center flex-shrink-0">
                      <FileText size={18} className="text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-on-surface truncate">
                        {doc.doc_name}
                      </p>
                      <p className="text-[11px] text-on-surface-muted font-mono mt-0.5 truncate">
                        {doc.doc_id.slice(0, 12)}...
                      </p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-tertiary/10 text-tertiary rounded-full text-[10px] font-label font-medium uppercase tracking-wider">
                    <CheckCircle size={10} />
                    Indexed
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={closeModal}
        >
          <div
            className="bg-surface-high rounded-2xl w-full max-w-lg p-8 relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={closeModal}
              className="absolute top-4 right-4 text-on-surface-muted hover:text-on-surface transition-colors"
            >
              <X size={18} />
            </button>

            <h3 className="text-xl font-semibold text-on-surface mb-2">Upload document</h3>
            <p className="text-sm text-on-surface-muted mb-6">
              PDF, Markdown (.md), Text (.txt), Word (.docx) — max 50MB
            </p>

            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl h-48 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
                dragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-outline/30 hover:border-outline/60'
              }`}
            >
              {uploadStatus === 'idle' && (
                <>
                  <Upload size={32} className="text-on-surface-muted" />
                  <p className="text-sm text-on-surface-dim">
                    Drop a file here or <span className="text-primary">click to browse</span>
                  </p>
                </>
              )}
              {uploadStatus === 'uploading' && (
                <>
                  <Loader2 size={32} className="text-primary animate-spin" />
                  <p className="text-sm text-on-surface-dim">{uploadFileName}</p>
                  <p className="text-xs text-on-surface-muted">Indexing...</p>
                </>
              )}
              {uploadStatus === 'success' && (
                <>
                  <CheckCircle size={32} className="text-tertiary" />
                  <p className="text-sm text-on-surface-dim">{uploadFileName}</p>
                  <p className="text-xs text-tertiary">Indexed successfully</p>
                </>
              )}
              {uploadStatus === 'error' && (
                <>
                  <AlertCircle size={32} className="text-error" />
                  <p className="text-sm text-on-surface-dim">{uploadFileName}</p>
                  <p className="text-xs text-error">{uploadError}</p>
                </>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.md,.markdown,.txt,.docx"
              onChange={handleFileInput}
              className="hidden"
            />

            {(uploadStatus === 'success' || uploadStatus === 'error') && (
              <button
                onClick={() => { setUploadStatus('idle'); setUploadFileName(''); }}
                className="mt-4 w-full py-2.5 text-sm font-medium text-primary border border-primary/20 rounded-lg hover:bg-primary/5 transition-colors"
              >
                Upload another
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
