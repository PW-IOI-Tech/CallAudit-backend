import os
from pathlib import Path
from typing import Dict, List
from elevenlabs.client import ElevenLabs
from openai import AzureOpenAI
from config import get_llm_config

# Load configuration for LLM services
llm_config = get_llm_config()


class ElevenLabsSpeechService:
    """
    A wrapper class for the ElevenLabs Speech-to-Text API.

    This service handles the conversion of audio files into text transcripts,
    including speaker diarization and confidence scoring. It encapsulates the
    logic for interacting with the ElevenLabs 'scribe_v1' model.
    """

    def __init__(self):
        """
        Initializes the ElevenLabsSpeechService client.

        Raises:
            Exception: If the ElevenLabs API key is invalid or client initialization fails.
        """
        self.client = ElevenLabs(api_key=llm_config.elevenlabs_api_key)

    def transcribe_audio(self, audio_path: Path, language_code: str = "en") -> Dict:
        """
        Transcribes an audio file using the ElevenLabs Speech-to-Text API.

        Args:
            audio_path (Path): The path to the audio file to be transcribed.
            language_code (str, optional): The language code for the audio.
                                         Defaults to "en". Note: Hindi-IN ("hi-IN")
                                         is mapped to English ("en") for the model.

        Returns:
            Dict: A dictionary containing the full transcript, segments with timing
                  and speaker info, speaker-specific data, word timings (if available),
                  and confidence scores. The structure includes keys like 'full_transcript',
                  'segments', 'speakers', 'word_timings', 'confidence_scores',
                  and 'overall_confidence'.

        Raises:
            Exception: If the transcription process fails (e.g., API error, file read error).
        """
        try:
            # Read the audio file data
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()

            # Call the ElevenLabs Speech-to-Text API
            transcription = self.client.speech_to_text.convert(
                file=audio_data,
                model_id="scribe_v1",  # Uses the Scribe model for transcription
                tag_audio_events=True,  # Enables tagging of audio events (if supported)
                language_code=language_code if language_code != "hi-IN" else "en",
                diarize=True,  # Enable speaker diarization to identify different speakers
            )

            # Process the raw API response into a structured format
            return self._process_transcription_response(transcription)
        except Exception as e:
            raise Exception(f"ElevenLabs transcription failed: {str(e)}")

    def _process_transcription_response(self, transcription) -> Dict:
        """
        Processes the raw ElevenLabs transcription response into a standardized dictionary.

        This internal method extracts the full transcript, segments (with timing, speaker,
        text, confidence), calculates overall confidence, and prepares speaker-specific data.

        Args:
            transcription: The raw response object from the ElevenLabs API.

        Returns:
            Dict: A structured dictionary containing processed transcription data.
                  Includes 'full_transcript', 'segments', 'speakers', 'word_timings',
                  'confidence_scores', and 'overall_confidence'.
        """
        # Initialize the result structure
        result = {
            "full_transcript": "",
            "segments": [],
            "speakers": {},
            "word_timings": [],
            "confidence_scores": [],
            "overall_confidence": 0.9,  # Default confidence if processing fails
        }

        # Extract the full transcript text
        if hasattr(transcription, "text"):
            result["full_transcript"] = transcription.text
        elif hasattr(transcription, "transcript"):
            result["full_transcript"] = transcription.transcript
        else:
            result["full_transcript"] = str(transcription)

        # Process segments if available from the API response
        if hasattr(transcription, "segments") and transcription.segments:
            for i, segment in enumerate(transcription.segments):
                # Extract segment details, providing defaults if attributes are missing
                segment_data = {
                    "start_time": getattr(
                        segment, "start_time", i * 5.0
                    ),  # Default timing
                    "end_time": getattr(
                        segment, "end_time", (i + 1) * 5.0
                    ),  # Default timing
                    "text": getattr(segment, "text", ""),
                    "speaker": getattr(
                        segment, "speaker", f"Speaker {i % 2}"
                    ),  # Alternate speakers
                    "confidence": getattr(
                        segment, "confidence", 0.9
                    ),  # Default confidence
                }
                # Calculate duration based on start and end times
                segment_data["duration"] = (
                    segment_data["end_time"] - segment_data["start_time"]
                )
                result["segments"].append(segment_data)

        # Fallback: Create pseudo-segments if API doesn't provide them but transcript exists
        if not result["segments"] and result["full_transcript"]:
            words = result["full_transcript"].split()
            words_per_segment = 20  # Number of words per pseudo-segment
            for i in range(0, len(words), words_per_segment):
                segment_words = words[i : i + words_per_segment]
                segment_text = " ".join(segment_words)
                # Assign pseudo-timing and speaker
                segment_data = {
                    "start_time": i * 0.5,
                    "end_time": (i + len(segment_words)) * 0.5,
                    "text": segment_text,
                    "speaker": f"Speaker {i // words_per_segment % 2}",  # Alternate speakers
                    "confidence": 0.9,  # Default confidence
                    "duration": len(segment_words) * 0.5,
                }
                result["segments"].append(segment_data)

        # If segments were processed, extract speaker-specific information
        if result["segments"]:
            result["speakers"] = self._extract_speaker_segments(result["segments"])

        # Calculate overall confidence based on segment confidences
        if result["segments"]:
            confidences = [seg["confidence"] for seg in result["segments"]]
            result["overall_confidence"] = sum(confidences) / len(confidences)
        else:
            result["overall_confidence"] = 0.9  # Use default if no segments

        return result

    def _extract_speaker_segments(self, segments: List[Dict]) -> Dict:
        """
        Aggregates segment data by speaker to provide speaker-specific statistics.

        Calculates total words spoken, total speaking duration, average confidence,
        and concatenated text for each identified speaker.

        Args:
            segments (List[Dict]): A list of segment dictionaries, each containing
                                 'speaker', 'text', 'duration', and 'confidence'.

        Returns:
            Dict: A dictionary mapping speaker IDs to their aggregated data.
                  Keys are speaker IDs (e.g., "Speaker 0"), values are dictionaries
                  with keys 'words', 'total_duration', 'word_count', 'confidence_scores',
                  'text', and 'avg_confidence'.
        """
        speakers = {}
        # Iterate through segments and accumulate data per speaker
        for segment in segments:
            speaker_id = segment["speaker"]
            if speaker_id not in speakers:
                # Initialize data structure for a new speaker
                speakers[speaker_id] = {
                    "words": [],
                    "total_duration": 0,
                    "word_count": 0,
                    "confidence_scores": [],
                    "text": "",  # Will be concatenated text
                    "avg_confidence": 0.0,
                }
            speaker_data = speakers[speaker_id]
            # Update speaker statistics with current segment data
            if segment["text"]:
                speaker_data["text"] += " " + segment["text"]  # Concatenate text
                speaker_data["word_count"] += len(
                    segment["text"].split()
                )  # Count words
                speaker_data["total_duration"] += segment["duration"]  # Add duration
                speaker_data["confidence_scores"].append(
                    segment["confidence"]
                )  # Store confidence

        # Calculate average confidence for each speaker after processing all segments
        for speaker_id, data in speakers.items():
            if data["confidence_scores"]:
                data["avg_confidence"] = sum(data["confidence_scores"]) / len(
                    data["confidence_scores"]
                )
            data["text"] = data["text"].strip()  # Clean up final text string

        return speakers

    def get_supported_languages(self) -> List[str]:
        """
        Returns a list of language codes supported by the ElevenLabs transcription model.

        Note: The actual language used in `transcribe_audio` for hi-IN is mapped to 'en'.

        Returns:
            List[str]: A list of supported language codes (e.g., 'en', 'es', 'fr').
        """
        return [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh",
            "ja",
            "hu",
            "ko",
            "hi",
        ]


class AzureOpenAIService:
    """
    A wrapper class for interacting with Azure OpenAI services for conversation analysis.

    This service provides methods to analyze conversation transcripts using Azure OpenAI
    models. It handles tasks like summarization, sentiment analysis, anomaly detection,
    keyword extraction, and detailed conversation analysis. Requires valid Azure OpenAI
    configuration.
    """

    def __init__(self):
        """
        Initializes the AzureOpenAI client using configuration from `llm_config`.

        Logs a warning if client initialization fails, setting client and deployment to None.
        """
        try:
            self.client = AzureOpenAI(
                azure_endpoint=llm_config.azure_openai_endpoint,
                api_key=llm_config.azure_openai_api_key,
                api_version=llm_config.azure_openai_api_version,
            )
            self.deployment = llm_config.azure_openai_deployment
        except Exception as e:
            print(f"Warning: Could not initialize Azure OpenAI client: {str(e)}")
            self.client = None
            self.deployment = None

    def analyze_conversation(self, transcript: str, speakers_data: Dict) -> Dict:
        """
        Performs a comprehensive analysis of a conversation transcript.

        Uses the configured Azure OpenAI model to generate insights on summary, topics,
        emotional journey, communication patterns, conflict points, decisions, dynamics,
        and recommendations.

        Args:
            transcript (str): The full conversation transcript text.
            speakers_data (Dict): Speaker information, typically from ElevenLabs processing.

        Returns:
            Dict: A dictionary containing the 'analysis' (the detailed text response from
                  the LLM) and 'usage' (token usage information from the API call).
                  Returns an error message in 'analysis' if the service is unavailable
                  or the call fails.
        """
        try:
            # Check if the client was initialized successfully
            if self.client is None:
                return {"analysis": "Azure OpenAI service not available", "usage": None}

            # Define the system prompt to guide the LLM's analysis
            system_prompt = (
                "You are an expert conversation analyst. Analyze the provided conversation transcript and provide "
                "comprehensive insights including: 1. Overall conversation summary 2. Key topics discussed 3. Emotional "
                "journey and tone changes 4. Communication patterns 5. Conflict resolution or tension points 6. "
                "Decision-making moments 7. Relationship dynamics 8. Important insights and recommendations"
            )

            # Make the API call to Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Transcript:\n{transcript}\nSpeaker Info:\n{self._format_speaker_info(speakers_data)}",
                    },
                ],
                max_tokens=1500,  # Limit the response length
                temperature=0.3,  # Low temperature for more deterministic/factual output
            )

            # Return the analysis and token usage
            return {
                "analysis": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            # Return an error message if analysis fails
            return {"analysis": f"Analysis failed: {str(e)}", "usage": None}

    def generate_conversation_summary(
        self, transcript: str, speakers_data: Dict  # speakers_data seems unused here
    ) -> Dict:
        """
        Generates a concise summary of a conversation transcript.

        Focuses on main topics, key decisions, action items, overall tone, and important quotes.

        Args:
            transcript (str): The full conversation transcript text.
            speakers_data (Dict): Speaker information (currently unused in the prompt).

        Returns:
            Dict: A dictionary containing the 'summary' (the text response from the LLM)
                  and 'usage' (token usage information). Returns an error message in 'summary'
                  if the call fails.
        """
        try:
            # Define the system prompt for summarization
            system_prompt = (
                "Create a concise but comprehensive summary of this conversation including: "
                "1. Main topics discussed 2. Key decisions made 3. Action items or next steps "
                "4. Overall tone and outcome 5. Important quotes or statements"
            )

            # Make the API call to Azure OpenAI for summarization
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Summarize this conversation:\n{transcript}",
                    },
                ],
                max_tokens=800,  # Limit the summary length
                temperature=0.3,  # Low temperature for factual summary
            )

            # Return the summary and token usage
            return {
                "summary": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            # Return an error message if summary generation fails
            return {"summary": f"Summary generation failed: {str(e)}", "usage": None}

    def detect_anomalies(self, transcript):
        """
        Identifies potential emotional triggers or anomalies in a conversation transcript.

        Looks for conflict points, sudden tone shifts, and confusion or contradiction.

        Args:
            transcript (str): The full conversation transcript text.

        Returns:
            str: A string containing the detected anomalies or an error message.
        """
        # Define the prompt for anomaly detection
        prompt = (
            "Identify emotional triggers or anomalies in this transcript:\n"
            "- Conflict points\n- Sudden tone shifts\n- Confusion or contradiction"
        )

        # Make the API call to Azure OpenAI for anomaly detection
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are a conversation anomaly detector.",
                },
                {
                    "role": "user",
                    "content": transcript,
                },  # Provide the transcript directly
            ],
            max_tokens=500,  # Limit the response length
        )

        # Return the detected anomalies (or error message)
        return response.choices[0].message.content.strip()

    def _format_speaker_info(self, speakers_data: Dict) -> str:
        """
        Formats speaker data dictionary into a human-readable string.

        Used internally to provide structured speaker information to the LLM prompts.

        Args:
            speakers_data (Dict): A dictionary containing speaker statistics.

        Returns:
            str: A formatted string representing the speaker information.
        """
        formatted = []
        # Iterate through speaker data and format each speaker's information
        for speaker_tag, data in speakers_data.items():
            formatted.append(f"Speaker {speaker_tag}:")
            formatted.append(f"  - Total words: {data.get('word_count', 0)}")
            formatted.append(
                f"  - Speaking time: {data.get('total_duration', 0):.2f} seconds"
            )
            formatted.append(
                f"  - Average confidence: {data.get('avg_confidence', 0):.2f}\n"
            )
        # Join all formatted lines into a single string
        return "\n".join(formatted)

    def get_customer_sentiment_score(self, transcript: str) -> int:
        """
        Analyzes the customer's overall sentiment from the conversation transcript.

        Returns a numerical score indicating sentiment: 1 (positive), 0 (neutral), -1 (negative).

        Args:
            transcript (str): The full conversation transcript text.

        Returns:
            int: The sentiment score (1, 0, or -1).

        Raises:
            Exception: If the API call fails or the response cannot be parsed to an integer.
        """
        try:
            # Define the prompt to instruct the LLM to return only a number
            prompt = (
                "Analyze the following conversation and return only one number as output:\n"
                "- Return 1 if the customer's overall sentiment is positive (interested, happy, satisfied)\n"
                "- Return 0 if the customer's sentiment is neutral (uncertain, general inquiry)\n"
                "- Return -1 if the customer sounds negative (angry, upset, disinterested)\n"
                "Do not explain. Just return one of these numbers: 1, 0, or -1.\n"
                f"Transcript:\n{transcript}".strip()
            )

            # Make the API call to Azure OpenAI for sentiment scoring
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a call center sentiment analysis model.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=5,  # Very short response expected (single digit)
                temperature=0,  # Deterministic output preferred
            )

            # Extract and parse the result
            result = response.choices[0].message.content.strip()
            score = int(result)
            assert score in [-1, 0, 1]  # Ensure the score is valid
            return score
        except Exception as e:
            # Re-raise the exception if parsing or API call fails
            raise e

    def extract_keywords(self, transcript):
        """
        Extracts a list of keywords from the conversation transcript.

        Args:
            transcript (str): The full conversation transcript text.

        Returns:
            List[str]: A list of extracted keywords.
        """
        # Define the prompt for keyword extraction
        prompt = "Extract 5 to 10 keywords from this transcript (comma-separated):"

        # Make the API call to Azure OpenAI for keyword extraction
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You extract keywords from customer transcripts.",
                },
                {"role": "user", "content": transcript},  # Provide the transcript
            ],
            max_tokens=50,  # Limit the response length for keywords
        )

        # Parse the comma-separated keywords from the response
        return [kw.strip() for kw in response.choices[0].message.content.split(",")]

    # Note: This method is duplicated in the original code. Keeping the first definition.
    # def _format_speaker_info(self, speakers_data: Dict) -> str:
    #     ... (implementation is identical to the one above)

    def get_sentiment(self, transcript):
        """
        Classifies the overall sentiment of the conversation transcript.

        Similar to `get_customer_sentiment_score` but uses a slightly different prompt.

        Args:
            transcript (str): The full conversation transcript text.

        Returns:
            int: The sentiment classification (1 for positive, 0 for neutral, -1 for negative).
                 Returns 0 if parsing fails.
        """
        # Define the prompt for sentiment classification
        prompt = (
            "Classify the customer's overall sentiment:\n"
            "- Return 1 if positive\n- 0 if neutral\n- -1 if negative\n"
            "Transcript:\n" + transcript
        )

        # Make the API call to Azure OpenAI for sentiment classification
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,  # Short response expected
            temperature=0,  # Deterministic output
        )

        # Attempt to parse the response as an integer
        try:
            return int(response.choices[0].message.content.strip())
        except:
            return 0  # Return neutral sentiment on parsing error

    def estimate_ai_confidence(self, usage: Dict) -> float:
        """
        Estimates the AI model's confidence based on token usage ratio.

        Calculates confidence as 1.0 minus the ratio of prompt tokens to total tokens.

        Args:
            usage (Dict): A dictionary containing token usage information, typically
                        from an OpenAI API response (e.g., {'prompt_tokens': X, 'total_tokens': Y}).

        Returns:
            float: An estimated confidence score between 0.0 and 1.0.
                   Returns 0.5 if calculation fails.
        """
        """Estimate AI's confidence score based on token ratio"""
        try:
            # Extract token counts, defaulting to 1 to avoid division by zero
            prompt_tokens = usage.get("prompt_tokens", 1)
            total_tokens = usage.get("total_tokens", 1)

            # Calculate the ratio of prompt tokens to total tokens
            ratio = prompt_tokens / total_tokens

            # Estimate confidence as the inverse of the prompt ratio
            confidence_score = round(1.0 - ratio, 2)
            return confidence_score
        except Exception:
            return 0.5  # Return default confidence on error
