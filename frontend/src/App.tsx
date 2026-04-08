import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Shell } from './components/Shell';
import { ChatPage } from './pages/Chat';
import { KnowledgeBasePage } from './pages/KnowledgeBase';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/knowledge" element={<KnowledgeBasePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
