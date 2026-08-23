import { Inject, Injectable } from '@nestjs/common';
import { Repository } from 'typeorm';
import { Tienda } from './entities';

@Injectable()
export class TiendaRepository {
  constructor(
    @Inject('TIENDA_REPOSITORY')
    private repository: Repository<Tienda>,
  ) {}

  async create(tienda: Partial<Tienda>): Promise<Tienda> {
    const newTienda = this.repository.create(tienda);
    return this.repository.save(newTienda);
  }

  async findAll(): Promise<Tienda[]> {
    return this.repository.find();
  }

  async findById(id: string): Promise<Tienda | null> {
    return this.repository.findOne({ where: { id } });
  }

  async update(
    id: string,
    updates: Partial<Tienda>,
  ): Promise<Tienda | null> {
    await this.repository.update(id, updates);
    return this.findById(id);
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.repository.delete(id);
    return (result.affected ?? 0) > 0;
  }
}