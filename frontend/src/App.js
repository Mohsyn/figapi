import { useState, useEffect } from 'react';
import '@/App.css';
import axios from 'axios';
import ReactJson from 'react-json-view';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { Code, Play, Save, Star, Clock, Trash2, Copy, BookOpen, AlertCircle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FIGMA_ENDPOINTS = {
  Files: [
    { name: 'Get file', endpoint: '/files/:file_key', method: 'GET', desc: 'Get a Figma file', example: '/files/YOUR_FILE_KEY' },
    { name: 'Get page only', endpoint: '/files/:file_key', method: 'PAGE', desc: 'Get only first page (canvas) from file', example: '/files/YOUR_FILE_KEY' },
    { name: 'Get file nodes', endpoint: '/files/:file_key/nodes', method: 'GET', desc: 'Get specific nodes from a file', example: '/files/YOUR_FILE_KEY/nodes?ids=1:2' },
    { name: 'Get images', endpoint: '/images/:file_key', method: 'GET', desc: 'Render images from file nodes', example: '/images/YOUR_FILE_KEY?ids=1:2&format=png' },
    { name: 'Get image fills', endpoint: '/files/:file_key/images', method: 'GET', desc: 'Get download links for images', example: '/files/YOUR_FILE_KEY/images' }
  ],
  Comments: [
    { name: 'Get comments', endpoint: '/files/:file_key/comments', method: 'GET', desc: 'Get comments from a file', example: '/files/YOUR_FILE_KEY/comments' },
    { name: 'Post comment', endpoint: '/files/:file_key/comments', method: 'POST', desc: 'Post a new comment', example: '/files/YOUR_FILE_KEY/comments' }
  ],
  Users: [
    { name: 'Get me', endpoint: '/me', method: 'GET', desc: 'Get current user info', example: '/me' }
  ],
  Projects: [
    { name: 'Get team projects', endpoint: '/teams/:team_id/projects', method: 'GET', desc: 'List projects for a team', example: '/teams/YOUR_TEAM_ID/projects' },
    { name: 'Get project files', endpoint: '/projects/:project_id/files', method: 'GET', desc: 'List files in a project', example: '/projects/YOUR_PROJECT_ID/files' }
  ],
  Webhooks: [
    { name: 'List webhooks', endpoint: '/webhooks/:team_id', method: 'GET', desc: 'List webhooks for a team', example: '/webhooks/YOUR_TEAM_ID' },
    { name: 'Create webhook', endpoint: '/webhooks', method: 'POST', desc: 'Create a new webhook', example: '/webhooks' },
    { name: 'Delete webhook', endpoint: '/webhooks/:webhook_id', method: 'DELETE', desc: 'Delete a webhook', example: '/webhooks/YOUR_WEBHOOK_ID' }
  ],
  Versions: [
    { name: 'Get file versions', endpoint: '/files/:file_key/versions', method: 'GET', desc: 'Get version history', example: '/files/YOUR_FILE_KEY/versions' }
  ]
};

function App() {
  const [figmaToken, setFigmaToken] = useState('');
  const [showTokenDialog, setShowTokenDialog] = useState(false);
  const [method, setMethod] = useState('GET');
  const [endpoint, setEndpoint] = useState('');
  const [headers, setHeaders] = useState('');
  const [body, setBody] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savedRequests, setSavedRequests] = useState([]);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('builder');
  const [selectedCategory, setSelectedCategory] = useState('Files');

  useEffect(() => {
    const token = localStorage.getItem('figma_token');
    if (token) {
      setFigmaToken(token);
    }
    loadSavedRequests();
    loadHistory();
  }, []);

  const saveToken = () => {
    localStorage.setItem('figma_token', figmaToken);
    setShowTokenDialog(false);
    toast.success('Token saved successfully');
  };

  const loadSavedRequests = async () => {
    try {
      const res = await axios.get(`${API}/saved-requests`);
      setSavedRequests(res.data);
    } catch (error) {
      console.error('Failed to load saved requests', error);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${API}/request-history`);
      setHistory(res.data);
    } catch (error) {
      console.error('Failed to load history', error);
    }
  };

  const executeRequest = async () => {
    if (!figmaToken) {
      toast.error('Please add your Figma token first');
      setShowTokenDialog(true);
      return;
    }

    if (!endpoint) {
      toast.error('Please enter an endpoint');
      return;
    }

    // Check for placeholder parameters
    if (endpoint.includes(':')) {
      toast.error('Please replace placeholder parameters (e.g., :file_key) with actual values');
      return;
    }

    setLoading(true);
    try {
      const requestHeaders = {
        'X-Figma-Token': figmaToken,
        'Content-Type': 'application/json',
        ...parseHeaders()
      };

      // Use different endpoint for PAGE method
      const apiEndpoint = method === 'PAGE' ? `${API}/figma/page` : `${API}/figma/proxy`;
      
      const res = await axios.post(apiEndpoint, {
        method: method === 'PAGE' ? 'GET' : method,
        endpoint,
        headers: requestHeaders,
        body: body ? JSON.parse(body) : null
      });

      setResponse(res.data);
      toast.success('Request executed successfully');
      loadHistory();
    } catch (error) {
      setResponse({
        error: true,
        message: error.response?.data?.detail || error.message
      });
      toast.error('Request failed');
    } finally {
      setLoading(false);
    }
  };

  const parseHeaders = () => {
    if (!headers) return {};
    try {
      return JSON.parse(headers);
    } catch {
      const headerObj = {};
      headers.split('\n').forEach(line => {
        const [key, value] = line.split(':');
        if (key && value) {
          headerObj[key.trim()] = value.trim();
        }
      });
      return headerObj;
    }
  };

  const saveRequest = async () => {
    const name = prompt('Enter a name for this request:');
    if (!name) return;

    try {
      await axios.post(`${API}/saved-requests`, {
        name,
        method,
        endpoint,
        headers: parseHeaders(),
        body,
        category: selectedCategory
      });
      toast.success('Request saved');
      loadSavedRequests();
    } catch (error) {
      toast.error('Failed to save request');
    }
  };

  const loadRequest = (req) => {
    setMethod(req.method);
    setEndpoint(req.endpoint);
    setHeaders(JSON.stringify(req.headers, null, 2));
    setBody(req.body || '');
    setActiveTab('builder');
  };

  const deleteRequest = async (id) => {
    try {
      await axios.delete(`${API}/saved-requests/${id}`);
      toast.success('Request deleted');
      loadSavedRequests();
    } catch (error) {
      toast.error('Failed to delete request');
    }
  };

  const toggleFavorite = async (id, isFavorite) => {
    try {
      await axios.put(`${API}/saved-requests/${id}`, { is_favorite: !isFavorite });
      loadSavedRequests();
    } catch (error) {
      toast.error('Failed to update favorite');
    }
  };

  const clearHistory = async () => {
    try {
      await axios.delete(`${API}/request-history`);
      setHistory([]);
      toast.success('History cleared');
    } catch (error) {
      toast.error('Failed to clear history');
    }
  };

  const loadExample = (example) => {
    setMethod(example.method);
    setEndpoint(example.endpoint);
    setActiveTab('builder');
    toast.info(`Loaded: ${example.name}`);
  };

  const copyResponse = () => {
    navigator.clipboard.writeText(JSON.stringify(response, null, 2));
    toast.success('Response copied to clipboard');
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <Code className="header-icon" />
            <h1 className="header-title">Figma API Playground</h1>
          </div>
          <Button 
            variant="outline" 
            onClick={() => setShowTokenDialog(true)}
            className="token-button"
            data-testid="configure-token-button"
          >
            <AlertCircle className="icon" />
            {figmaToken ? 'Update Token' : 'Configure Token'}
          </Button>
        </div>
      </header>

      <div className="main-layout">
        <aside className="sidebar">
          <ScrollArea className="sidebar-scroll">
            <div className="sidebar-section">
              <h3 className="sidebar-title">API Endpoints</h3>
              {Object.keys(FIGMA_ENDPOINTS).map(category => (
                <div key={category} className="category-group">
                  <button
                    className={`category-button ${selectedCategory === category ? 'active' : ''}`}
                    onClick={() => setSelectedCategory(category)}
                    data-testid={`category-${category.toLowerCase()}`}
                  >
                    {category}
                  </button>
                  {selectedCategory === category && (
                    <div className="endpoint-list">
                      {FIGMA_ENDPOINTS[category].map((ep, idx) => (
                        <button
                          key={idx}
                          className="endpoint-item"
                          onClick={() => loadExample(ep)}
                          data-testid={`endpoint-${ep.name.toLowerCase().replace(/\s+/g, '-')}`}
                        >
                          <span className={`method-badge ${ep.method.toLowerCase()}`}>{ep.method}</span>
                          <span className="endpoint-name">{ep.name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="sidebar-section">
              <h3 className="sidebar-title">Saved Requests</h3>
              {savedRequests.length === 0 ? (
                <p className="empty-state">No saved requests</p>
              ) : (
                savedRequests.map(req => (
                  <div key={req.id} className="saved-request-item" data-testid="saved-request-item">
                    <button onClick={() => loadRequest(req)} className="request-button">
                      {req.name}
                    </button>
                    <div className="request-actions">
                      <button onClick={() => toggleFavorite(req.id, req.is_favorite)} data-testid="toggle-favorite">
                        <Star className={`icon-small ${req.is_favorite ? 'favorited' : ''}`} />
                      </button>
                      <button onClick={() => deleteRequest(req.id)} data-testid="delete-request">
                        <Trash2 className="icon-small" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </aside>

        <main className="content">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="tabs-container">
            <TabsList className="tabs-list">
              <TabsTrigger value="builder" data-testid="builder-tab">Request Builder</TabsTrigger>
              <TabsTrigger value="history" data-testid="history-tab">History</TabsTrigger>
            </TabsList>

            <TabsContent value="builder" className="tab-content">
              <Card className="request-card">
                <div className="request-header">
                  <div className="method-endpoint">
                    <Select value={method} onValueChange={setMethod}>
                      <SelectTrigger className="method-select" data-testid="method-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="GET">GET</SelectItem>
                        <SelectItem value="POST">POST</SelectItem>
                        <SelectItem value="PUT">PUT</SelectItem>
                        <SelectItem value="DELETE">DELETE</SelectItem>
                        <SelectItem value="PAGE">PAGE</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      value={endpoint}
                      onChange={(e) => setEndpoint(e.target.value)}
                      placeholder="/me (try this first to test your token)"
                      className="endpoint-input"
                      data-testid="endpoint-input"
                    />
                  </div>
                  <div className="action-buttons">
                    <Button onClick={saveRequest} variant="outline" data-testid="save-request-button">
                      <Save className="icon" />
                      Save
                    </Button>
                    <Button onClick={executeRequest} disabled={loading} data-testid="execute-button">
                      <Play className="icon" />
                      {loading ? 'Executing...' : 'Execute'}
                    </Button>
                  </div>
                </div>

                <div className="help-banner" data-testid="help-banner">
                  <BookOpen className="help-icon" />
                  <div className="help-text">
                    <strong>Quick Start:</strong> Try <code>/me</code> first to verify your token. 
                    For file endpoints, replace <code>:file_key</code> with your actual file key from the Figma URL 
                    (e.g., <code>https://figma.com/file/ABC123/...</code> → use <code>ABC123</code>)
                  </div>
                </div>

                <div className="request-body">
                  <div className="input-section">
                    <Label>Headers (JSON or key:value per line)</Label>
                    <Textarea
                      value={headers}
                      onChange={(e) => setHeaders(e.target.value)}
                      placeholder='{"Custom-Header": "value"}'
                      className="code-textarea"
                      rows={4}
                      data-testid="headers-input"
                    />
                  </div>

                  {(method === 'POST' || method === 'PUT') && (
                    <div className="input-section">
                      <Label>Request Body (JSON)</Label>
                      <Textarea
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        placeholder='{"message": "Hello"}'
                        className="code-textarea"
                        rows={6}
                        data-testid="body-input"
                      />
                    </div>
                  )}
                </div>
              </Card>

              {response && (
                <Card className="response-card">
                  <div className="response-header">
                    <h3 className="response-title">Response</h3>
                    <Button variant="ghost" size="sm" onClick={copyResponse} data-testid="copy-response">
                      <Copy className="icon" />
                      Copy
                    </Button>
                  </div>
                  <div className="response-body">
                    {response.error ? (
                      <div className="error-message" data-testid="error-message">
                        <AlertCircle className="error-icon" />
                        {response.message}
                      </div>
                    ) : (
                      <div data-testid="response-json">
                        <div className="status-badge">Status: {response.status_code}</div>
                        <ReactJson
                          src={response.data}
                          theme="monokai"
                          collapsed={1}
                          displayDataTypes={false}
                          displayObjectSize={false}
                          enableClipboard={true}
                          style={{ background: 'transparent', fontSize: '13px' }}
                        />
                      </div>
                    )}
                  </div>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="history" className="tab-content">
              <Card className="history-card">
                <div className="history-header">
                  <h3 className="history-title">
                    <Clock className="icon" />
                    Request History
                  </h3>
                  <Button variant="destructive" size="sm" onClick={clearHistory} data-testid="clear-history">
                    <Trash2 className="icon" />
                    Clear All
                  </Button>
                </div>
                <ScrollArea className="history-scroll">
                  {history.length === 0 ? (
                    <p className="empty-state">No history yet</p>
                  ) : (
                    history.map((item, idx) => (
                      <div key={idx} className="history-item" data-testid="history-item">
                        <div className="history-item-header">
                          <span className={`method-badge ${item.method.toLowerCase()}`}>{item.method}</span>
                          <span className="history-endpoint">{item.endpoint}</span>
                          <span className={`status-badge ${item.status_code === 200 ? 'success' : 'error'}`}>
                            {item.status_code}
                          </span>
                        </div>
                        <div className="history-timestamp">
                          {new Date(item.timestamp).toLocaleString()}
                        </div>
                      </div>
                    ))
                  )}
                </ScrollArea>
              </Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>

      <Dialog open={showTokenDialog} onOpenChange={setShowTokenDialog}>
        <DialogContent className="token-dialog" data-testid="token-dialog">
          <DialogHeader>
            <DialogTitle>Configure Figma Token</DialogTitle>
            <DialogDescription>
              To use the Figma API, you need a Personal Access Token.
            </DialogDescription>
          </DialogHeader>
          <div className="token-instructions">
            <h4>How to get your Figma token:</h4>
            <ol>
              <li>Go to <a href="https://www.figma.com/developers/api#access-tokens" target="_blank" rel="noopener noreferrer">Figma Settings</a></li>
              <li>Scroll to "Personal access tokens"</li>
              <li>Click "Generate new token"</li>
              <li>Copy the token and paste it below</li>
            </ol>
          </div>
          <div className="token-input-section">
            <Label>Personal Access Token</Label>
            <Input
              type="password"
              value={figmaToken}
              onChange={(e) => setFigmaToken(e.target.value)}
              placeholder="Enter your Figma token"
              data-testid="token-input"
            />
          </div>
          <Button onClick={saveToken} className="save-token-button" data-testid="save-token-button">
            Save Token
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default App;