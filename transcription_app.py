import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import os
from openai import OpenAI
from typing import List

MODEL = "gpt-4o-mini"
os.environ["API_KEY"] = st.secrets["API_KEY"]
client = OpenAI(api_key = API_KEY)
class TranscriptionProcessor:
    def get_video_transcript(self, url: str) -> str:
        try:
            video_id = url.split("v=")[1].split("&")[0]
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(segment['text'] for segment in transcript_list)
        except Exception as e:
            raise Exception(f"Failed to get transcript: {str(e)}")

    def chunk_text(self, text: str, max_tokens: int = 10000) -> List[str]:
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_token_estimate = len(word) * 1.3
            if current_length + word_token_estimate > max_tokens:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_token_estimate
            else:
                current_chunk.append(word)
                current_length += word_token_estimate
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    def clean_transcript_chunk(self, chunk: str) -> str:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at cleaning transcripts. You remove unnecessary junk, correct odd capitalization, retain proper nouns, and make sure that formatting is fine. Do not change the meaning of the content. Add breaks at appropriate breaks in the conversation. When given a transcript, simply provide the cleaned up transcript, with NO commentary or notes."},
                    {"role": "user", "content": f"Clean this transcript: {chunk}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Failed to clean transcript chunk: {str(e)}")

    def save_to_file(self, hearing_id: int, raw_transcript: str, cleaned_transcript: str) -> None:
        try:
            os.makedirs('transcripts', exist_ok=True)
            raw_filename = f'transcripts/hearing_{hearing_id}_raw.txt'
            with open(raw_filename, 'w', encoding='utf-8') as f:
                f.write(raw_transcript)
            cleaned_filename = f'transcripts/hearing_{hearing_id}_cleaned.txt'
            with open(cleaned_filename, 'w', encoding='utf-8') as f:
                f.write(cleaned_transcript)
        except Exception as e:
            raise Exception(f"Failed to save files: {str(e)}")

    def process_single_video(self, hearing_id: int, url: str) -> (str, str):
        raw_transcript = self.get_video_transcript(url)
        chunks = self.chunk_text(raw_transcript)
        cleaned_chunks = []

        progress_bar = st.progress(0)
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks, start=1):
            cleaned_chunk = self.clean_transcript_chunk(chunk)
            cleaned_chunks.append(cleaned_chunk)

            progress_bar.progress(i / total_chunks)

        final_transcript = " ".join(cleaned_chunks)
        self.save_to_file(hearing_id, raw_transcript, final_transcript)
        return raw_transcript, final_transcript


def main():
    st.title("YouTube Transcript Processor")
    st.header("Transcribe and Clean YouTube Video Transcripts")
    
    hearing_id = st.text_input("Enter Hearing ID")
    url = st.text_input("Enter YouTube URL")
    
    if st.button("Process Video"):
        if hearing_id and url:
            try:
                processor = TranscriptionProcessor()
                raw_transcript, cleaned_transcript = processor.process_single_video(int(hearing_id), url)
                
                st.success("Processing completed successfully.")
                
                # Display download buttons for both transcripts
                st.download_button(
                    label="Download Raw Transcript",
                    data=raw_transcript,
                    file_name=f'hearing_{hearing_id}_raw.txt',
                    mime='text/plain'
                )
                
                st.download_button(
                    label="Download Cleaned Transcript",
                    data=cleaned_transcript,
                    file_name=f'hearing_{hearing_id}_cleaned.txt',
                    mime='text/plain'
                )

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.error("Please enter both a hearing ID and a YouTube URL.")


if __name__ == "__main__":
    main()