import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Input,
  IconButton,
  Text,
  Flex,
} from '@chakra-ui/react';
import { FaRegPaperPlane } from 'react-icons/fa';
import { LuSun, LuMoon } from 'react-icons/lu';
import { useColorMode, useColorModeValue } from './components/ui/color-mode';
import { SessionList } from './components/session-list';
import { A2AClient } from './client/client';
import { createTextMessageObject } from './client/helpers';
import type { Message, Session } from './client/schema';
import reactLogo from './assets/react.svg';
import './App.css';

// 상수 정의
const APP_NAME = 'weather_time_agent';
const USER_ID = 'self';

// Message에 id, timestamp를 추가한 타입
interface MessageWithMeta extends Message {
  timestamp: string;
}

function App() {
  const [sessionId, setSessionId] = useState<string>('');
  const [chats, setChats] = useState<MessageWithMeta[]>([]);
  const [input, setInput] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { colorMode, toggleColorMode } = useColorMode();

  // A2AClient 인스턴스 생성 (URL은 실제 서버 주소로 교체 필요)
  const a2aClient = useRef(new A2AClient({ url: import.meta.env.VITE_A2A_SERVER_URL }));

  // 2. 컴포넌트 마운트 시 sessionId 설정
  useEffect(() => {
    setSessionId(crypto.randomUUID()); // 새 세션 ID 생성
  }, []);

  useEffect(() => {
    const fetchSessions = async (appName: string, userId: string) => {
      try {
        const baseUrl = import.meta.env.VITE_A2A_SERVER_URL.replace(/\/$/, '');
        // TODO: The path /apps/weather_time_agent/users/self/sessions might need to be dynamic
        const response = await fetch(`${baseUrl}/apps/${appName}/users/${userId}/sessions`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          }
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const resultData = await response.json();
        setSessions(resultData.sessions);
      } catch (error) {
        console.error("Failed to fetch sessions:", error);
        // 사용자에게 에러를 알리거나, 기본 세션 목록을 설정하는 등의 처리를 할 수 있습니다.
        setSessions([]); // 에러 발생 시 빈 배열로 설정
      }
    };
    fetchSessions(APP_NAME, USER_ID);
  }, []);

  // 선택된 세션의 채팅 내역을 불러오는 함수
  const fetchChatHistory = async (currentSessionId: string) => {
    if (!currentSessionId) return;

    try {
      const baseUrl = import.meta.env.VITE_A2A_SERVER_URL.replace(/\/$/, '');
      const response = await fetch(`${baseUrl}/apps/${APP_NAME}/users/${USER_ID}/sessions/${currentSessionId}/messages`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        }
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const chatHistoryData = await response.json(); 
      // API 응답이 MessageWithMeta[]와 일치한다고 가정합니다.
      // 필요시 데이터 변환 로직 추가
      setChats(chatHistoryData); 
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
      setChats([]); // 에러 발생 시 채팅 내역 비우기
    }
  };

  // 메시지 전송 핸들러
  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    // 질문 메시지 추가
    const userMessage = createTextMessageObject(sessionId, 'user', text);
    const userMsg: MessageWithMeta = { ...userMessage, timestamp: new Date().toISOString() };
    setChats(prev => ([...prev, userMsg]));
    setInput('');
    // 서버에 메시지 전송
    try {
      // Create a new message object with APP_NAME and USER_ID
      const messageToSend = {
        ...userMessage,
        appName: APP_NAME,
        userId: USER_ID,
      };
      const result = await a2aClient.current.sendMessage(messageToSend);
      // Task 타입 처리
      if (result && 'artifacts' in result && result.artifacts?.[0]?.parts?.[0] && 'text' in result.artifacts[0].parts[0]) {
        const agentMessage = createTextMessageObject(sessionId, 'agent', result.artifacts[0].parts[0].text);
        const agentMsg: MessageWithMeta = { ...agentMessage, timestamp: new Date().toISOString() };
        setChats(prev => ([...prev, agentMsg]));
      }
      // Message 타입 처리
      else if (result && 'parts' in result && result.parts?.[0] && 'text' in result.parts[0]) {
        const agentMessage = createTextMessageObject(sessionId, 'agent', result.parts[0].text);
        const agentMsg: MessageWithMeta = { ...agentMessage, timestamp: new Date().toISOString() };
        setChats(prev => ([...prev, agentMsg]));
      }
    } catch (error) {
      const errorMsg: MessageWithMeta = { ...createTextMessageObject(sessionId, 'agent', '에러가 발생했습니다.'), timestamp: new Date().toISOString() };
      setChats(prev => ([...prev, errorMsg]));
    }
  };

  // 세션 클릭 핸들러
  const handleSessionClick = (clickedSessionId: string) => {
    setSessionId(clickedSessionId); // 선택된 세션 ID로 업데이트
    fetchChatHistory(clickedSessionId); // 선택된 세션의 채팅 내역 불러오기
  };

  // Enter 키 입력 핸들러
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  // 스크롤 항상 아래로
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chats]);

  // 메시지 버블 색상
  const userMessageBoxBg = useColorModeValue('blue.500', 'blue.300');
  const botMessageBoxBg = useColorModeValue('gray.200', 'gray.700');
  const userMessageBoxColor = useColorModeValue('white', 'gray.900');
  const botMessageBoxColor = useColorModeValue('black', 'white');

  return (
    <HStack height="100vh" width="100%" gap={0} align="stretch">
      <SessionList sessions={sessions} onSessionClick={handleSessionClick} />
      <Flex
        direction="column"
        height="100%"
        flex={1}
        bg={useColorModeValue('white', 'gray.800')}
      >
        {/* 상단 헤더 */}
        <Flex p={3} justifyContent="space-between" alignItems="center" borderWidth="1px" borderColor="gray.200" borderRadius="2xl">
          <Flex align="center" gap={3}>
            <img src={reactLogo} alt="농협로고" style={{ width: 40, height: 40 }} />
            <Text fontWeight="bold" fontSize="xl">영업점 질의사항 대응 어시스턴트</Text>
          </Flex>
          <IconButton
            aria-label="Toggle theme"
            onClick={toggleColorMode}
            variant="ghost"
            borderRadius="full"
          >
            {colorMode === 'light' ? <LuMoon /> : <LuSun />}
          </IconButton>
        </Flex>
        {/* 날짜 구분선 */}
        <Flex align="center" w="100%" maxW="600px" mx="auto" my={2}>
          <Box flex="1" h="1px" bg="gray.200" />
          <Text color="gray.500" fontSize="md" px={4} whiteSpace="nowrap">2025.05.21</Text>
          <Box flex="1" h="1px" bg="gray.200" />
        </Flex>
        {/* 메시지 표시 영역 */}
        <VStack
          flex="1"
          gap={4}
          overflowY="auto"
          p={4}
          align="stretch"
          maxW="600px"
          mx="auto"
          w="100%"
        >
          {chats.map((msg) => (
            <Flex
              key={msg.messageId}
              justify={msg.role === 'user' ? 'flex-end' : 'flex-start'}
            >
              {msg.role === 'user' && <Text fontSize="xs" color="gray.500" mt={1} textAlign={'right'} alignSelf="flex-end" mr={2}>{new Date(msg.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}</Text>}
              <Box
                bg={msg.role === 'user' ? userMessageBoxBg : botMessageBoxBg}
                color={msg.role === 'user' ? userMessageBoxColor : botMessageBoxColor}
                px={3}
                py={2}
                borderRadius="lg"
                maxWidth="70%"
              >
                <Text fontSize="sm" whiteSpace="pre-line" dangerouslySetInnerHTML={{ __html: (msg.parts?.[0] && 'text' in msg.parts[0] ? msg.parts[0].text : '') }} />
              </Box>
              {msg.role === 'agent' && <Text fontSize="xs" color="gray.500" mt={1} textAlign={'left'} alignSelf="flex-end" ml={2}>{new Date(msg.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}</Text>}
            </Flex>
          ))}
          <div ref={messagesEndRef} />
        </VStack>
        {/* 입력창 */}
        <HStack p={4} borderWidth="1px" borderColor="gray.200" borderRadius="2xl" maxW="600px" mx="auto" w="100%" bg={useColorModeValue('white', 'gray.800')}>
          <Input
            flex="1"
            ref={inputRef}
            placeholder="질의사항을 입력해주세요."
            borderRadius="full"
            bg={useColorModeValue('gray.100', 'gray.600')}
            size="lg"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <IconButton
            colorScheme="blue"
            aria-label="Send message"
            onClick={handleSend}
            borderRadius="full"
          >
            <FaRegPaperPlane />
          </IconButton>
        </HStack>
      </Flex>
    </HStack>
  );
}

export default App;
