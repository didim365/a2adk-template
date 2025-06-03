import { VStack, Text, Avatar, Box, HStack } from '@chakra-ui/react';
import type { Session, Event as SessionEvent, Part, TextPart } from '../client/schema';

interface SessionListProps {
  sessions: Session[];
  onSessionClick: (sessionId: string) => void;
}

export function SessionList(props: SessionListProps) {
  return (
    <VStack
      height="100%"
      width="250px"
      padding={4}
      borderRightWidth="1px"
      borderColor="gray.200"
      alignItems="stretch"
      gap={4}
    >
      <Text fontSize="xl" fontWeight="bold" marginBottom={4}>
        대화 목록
      </Text>
      <VStack flex={1} overflowY="auto" alignItems="stretch" gap={2}>
        {props.sessions.length > 0 && props.sessions.map((session: Session) => {
          const displayText = session.events
            ?.flatMap((event: SessionEvent) =>
              event.content?.parts
                ?.filter((part: Part): part is { text: string } & Part => typeof (part as any).text === 'string')
                .map((part) => (part as { text: string }).text) || []
            )
            .join(' ');
          return (
            <Box
              key={session.id}
              padding={2}
              borderRadius="md"
              _hover={{ bg: 'gray.100' }}
              cursor="pointer"
              onClick={() => props.onSessionClick(session.id)}
            >
              <Text>{displayText}</Text><Text fontSize="xs" color="gray.500">{new Date(session.last_update_time * 1000).toLocaleString()}</Text>
            </Box>
          );
        })}
      </VStack>
      <Box height="1px" backgroundColor="gray.200" marginY={4} />
      <Box marginTop="auto" paddingTop={4}>
        <HStack gap={3}>
          <Avatar.Root>
            <Avatar.Fallback name="농협인" />
          </Avatar.Root>
          <Text fontWeight="medium">농협인</Text>
        </HStack>
      </Box>
    </VStack>
  );
}
