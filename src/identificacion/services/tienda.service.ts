import {
  Injectable,
  NotFoundException,
} from '@nestjs/common';

import { Tienda } from '../repositories/entities';
import { TiendaRepository } from '../repositories/tienda.repository';

@Injectable()
export class TiendaService {
  constructor(
    private readonly tiendaRepository: TiendaRepository,
  ) {}

  async create(tienda: Partial<Tienda>): Promise<Tienda> {
    return this.tiendaRepository.create(tienda);
  }

  async findAll(): Promise<Tienda[]> {
    return this.tiendaRepository.findAll();
  }

  async findById(id: string): Promise<Tienda> {
    const tienda = await this.tiendaRepository.findById(id);

    if (!tienda) {
      throw new NotFoundException(
        `Tienda con id ${id} no encontrada`,
      );
    }

    return tienda;
  }

  async update(
    id: string,
    updates: Partial<Tienda>,
  ): Promise<Tienda> {
    const tienda = await this.tiendaRepository.findById(id);

    if (!tienda) {
      throw new NotFoundException(
        `Tienda con id ${id} no encontrada`,
      );
    }

    const updatedTienda = await this.tiendaRepository.update(
      id,
      updates,
    );

    return updatedTienda!;
  }

  async delete(id: string): Promise<void> {
    const tienda = await this.tiendaRepository.findById(id);

    if (!tienda) {
      throw new NotFoundException(
        `Tienda con id ${id} no encontrada`,
      );
    }

    await this.tiendaRepository.delete(id);
  }

  async exists(id: string): Promise<boolean> {
    const tienda = await this.tiendaRepository.findById(id);
    return !!tienda;
  }
}