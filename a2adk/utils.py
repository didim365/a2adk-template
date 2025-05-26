from uuid import uuid4
import httpx

from google.genai import types

from a2a.client import A2AClient
from a2a.types import (
  SendMessageRequest, 
  Part, 
  TextPart, 
  FilePart, 
  FileWithUri,
  FileWithBytes, 
  SendMessageRequest
  )


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    """Convert a list of A2A Part types into a list of Google GenAI Part types."""
    return [convert_a2a_part_to_genai(part) for part in parts]


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Convert a single A2A Part type into a Google GenAI Part type."""
    part = part.root
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    elif isinstance(part, FilePart):
        if isinstance(part.file, FileWithUri):
            return types.Part(
                file_data=types.FileData(
                    file_uri=part.file.uri, mime_type=part.file.mime_type
                )
            )
        elif isinstance(part.file, FileWithBytes):
            return types.Part(
                inline_data=types.Blob(
                    data=part.file.bytes, mime_type=part.file.mime_type
                )
            )
        else:
            raise ValueError(f'Unsupported file type: {type(part.file)}')
    else:
        raise ValueError(f'Unsupported part type: {type(part)}')


def convert_genai_parts_to_a2a(parts: list[types.Part]) -> list[Part]:
    """Convert a list of Google GenAI Part types into a list of A2A Part types."""
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        if (part.text or part.file_data or part.inline_data)
    ]


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Convert a single Google GenAI Part type into an A2A Part type."""
    if part.text:
        return TextPart(text=part.text)
    elif part.file_data:
        return FilePart(
            file=FileWithUri(
                uri=part.file_data.file_uri,
                mime_type=part.file_data.mime_type,
            )
        )
    elif part.inline_data:
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    else:
        raise ValueError(f'Unsupported part type: {part}')


async def send_a2a_message(request: SendMessageRequest, agent_endpoint: str):
    async with httpx.AsyncClient() as client:
        agent_client = A2AClient(
            httpx_client=client, 
            url=agent_endpoint
        )
        return await agent_client.send_message(request)
