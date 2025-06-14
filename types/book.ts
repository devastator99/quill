export interface Book {
  id: string;
  title: string;
  author: string;
  coverImage: string;
  publicationYear: number;
  progress?: number;
  rating: number;
  genre: string;
  pages: number;
  description: string;
  isbn: string;
}