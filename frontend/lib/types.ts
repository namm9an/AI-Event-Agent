export type Role = "user" | "super_admin";

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  role: Role;
}

export interface MeResponse {
  username: string;
  role: Role;
  expires_at: string;
}

export interface Speaker {
  id: string;
  event_id: string;
  name: string;
  designation: string;
  company: string;
  talk_title: string;
  talk_summary: string;
  linkedin_url: string;
  linkedin_bio: string;
  topic_links: string[];
  topic_category: string;
  previous_talks: string[];
  wikipedia_url: string;
}

export interface Event {
  id: string;
  name: string;
  description: string;
  date_text: string;
  location: string;
  city: string;
  status: string;
  category: string[];
  url: string;
  organizer: string;
  event_type: string;
  registration_url: string;
  image_url: string;
  speakers: Speaker[];
}

export interface ReportItem {
  id: string;
  report_date: string;
  file_name: string;
  created_at: string;
  status: string;
  size_bytes: number | null;
}

export interface SearchQuery {
  id: string;
  query: string;
  topic: string;
  is_active: boolean;
  priority: number;
}

export interface Schedule {
  timezone: string;
  scrape_time: string;
  report_time: string;
}
