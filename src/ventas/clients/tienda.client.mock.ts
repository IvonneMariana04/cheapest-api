import { Injectable } from '@nestjs/common';

@Injectable()
export class TiendaClient {
  private readonly baseUrl = 'http://localhost:3006/identification/stores';

  async exists(id: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/${id}`);

      return response.ok;
    } catch {
      return false;
    }
  }
}